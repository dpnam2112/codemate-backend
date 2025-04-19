from uuid import UUID
from dramatiq import actor
from sqlalchemy import select
from core.db.session import DB_MANAGER, Dialect
from core.db.utils import session_context
from machine.models.coding_submission import ProgrammingSubmission, ProgrammingTestResult, ProgrammingTestCase, SubmissionStatus
from machine.models.exercises import Exercises
import machine.services.judge0_client as judge0_client
from machine.services.code_exercise_assistant import CodeExerciseAssistantService
from core.logger import syslog
from worker import broker
from tasks.update_issues_summary import update_issues_summary


class StillProcessingError(Exception):
    pass

@actor(max_retries=3, min_backoff=10, max_backoff=60, broker=broker)
async def poll_judge0_submission_result(submission_id_str: str):
    submission_id = UUID(submission_id_str)
    async with session_context(DB_MANAGER[Dialect.POSTGRES]) as session:
        # Fetch test results
        stmt = select(ProgrammingTestResult).where(
            ProgrammingTestResult.submission_id == submission_id
        )
        result = await session.execute(stmt)
        test_results = result.scalars().all()

        if not test_results:
            syslog.warning(f"No test results found for submission {submission_id}")
            return

        pending_results = [tr for tr in test_results if tr.status in ("Processing", "In Queue")]
        tokens = [tr.judge0_token for tr in pending_results if tr.judge0_token]

        still_processing = False  # Always initialized

        if not pending_results:
            syslog.info(f"No test cases still in progress for submission {submission_id}")
        else:
            # Get corresponding test cases for Judge0 call
            test_cases = []
            for tr in pending_results:
                tc = await session.get(ProgrammingTestCase, tr.testcase_id)
                test_cases.append({"input": tc.input, "expected": tc.expected_output})

            # Poll Judge0 for result
            judge0_results = await judge0_client.get_submission_results(tokens, test_cases)

            for tr, res in zip(pending_results, judge0_results):
                tr.status = res["status"]
                tr.stdout = res["stdout"]
                tr.stderr = res["stderr"]
                tr.time = res.get("time")
                tr.memory = res.get("memory")

                if res["status"] in ["In Queue", "Processing"]:
                    still_processing = True

            if still_processing:
                raise StillProcessingError(f"Submission {submission_id} still has pending results.")

        # Determine submission status based on all test results
        all_accepted = all(tr.status == "Accepted" for tr in test_results)
        submission_status = SubmissionStatus.COMPLETED if all_accepted else SubmissionStatus.FAILED

        # Evaluate and update submission
        submission = await session.get(ProgrammingSubmission, submission_id)
        if not submission:
            syslog.error(f"Submission {submission_id} not found")
            return

        try:
            exercise = await session.get(Exercises, submission.exercise_id)
            if not exercise:
                syslog.error(f"Exercise not found for submission {submission_id}")
                return

            problem_description = exercise.description or "No description provided"

            eval_test_results = [{
                "status": tr.status,
                "stdout": tr.stdout,
                "stderr": tr.stderr
            } for tr in test_results]

            assistant_service = CodeExerciseAssistantService()
            evaluation = await assistant_service.evaluate_submission(
                code=submission.code,
                problem_description=problem_description,
                language_id=submission.judge0_language_id,
                test_results=eval_test_results
            )

            if evaluation:
                submission.llm_evaluation = evaluation.model_dump()
                syslog.info(f"Evaluated submission {submission_id} with score {evaluation.score}")
        except Exception as e:
            syslog.error(f"Error evaluating submission {submission_id}: {str(e)}")

        submission.status = submission_status
        await session.commit()
        syslog.info(f"Updated submission {submission_id} status to {submission.status}")

        # Trigger issues summary update
#        update_issues_summary.send(str(submission_id))
        syslog.info(f"Triggered issues summary update for submission {submission_id}")
