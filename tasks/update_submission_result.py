from uuid import UUID
from dramatiq import actor
from sqlalchemy import select
from core.db.session import DB_MANAGER, Dialect
from core.db.utils import session_context
from machine.models.coding_submission import ProgrammingSubmission, ProgrammingTestResult, ProgrammingTestCase, SubmissionStatus
import machine.services.judge0_client as judge0_client
from core.logger import syslog
from worker import broker


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

        pending_results = [tr for tr in test_results if tr.status == "Processing"]
        if not pending_results:
            syslog.info(f"Submission {submission_id} already processed")
            return

        tokens = [tr.judge0_token for tr in pending_results if tr.judge0_token]
        if not tokens:
            syslog.warning(f"No tokens available for submission {submission_id}")
            return

        test_cases = []
        for tr in pending_results:
            tc = await session.get(ProgrammingTestCase, tr.testcase_id)
            test_cases.append({"input": tc.input, "expected": tc.expected_output})

        judge0_results = await judge0_client.get_submission_results(tokens, test_cases)

        submission_status = SubmissionStatus.COMPLETED

        for tr, res in zip(pending_results, judge0_results):
            tr.status = res["status"]
            tr.stdout = res["stdout"]
            tr.stderr = res["stderr"]
            tr.time = res.get("time")
            tr.memory = res.get("memory")

            if res["status"] in ["In Queue", "Processing"]:
                submission_status = SubmissionStatus.PENDING
            elif res["status"] != "Accepted":
                submission_status = SubmissionStatus.FAILED

        # Update submission status
        submission = await session.get(ProgrammingSubmission, submission_id)
        if submission: submission.status = submission_status

        await session.flush()
        syslog.info(f"Updated submission {submission_id} status to {submission.status}")

