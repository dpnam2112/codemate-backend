from operator import and_
from typing import Optional, Sequence, TypedDict
from uuid import UUID

from openai import AsyncOpenAI, OpenAI
from sqlalchemy import func, select
from sqlalchemy.orm import noload, selectinload, with_loader_criteria
from core.controller import BaseController
from core.db.session import DB_MANAGER, DBSessionKeeper, Dialect
from core.db.utils import session_context
from core.exceptions.base import NotFoundException
from machine.models import Exercises
from machine.models.coding_assistant import CodingConversation, Conversation, Message
from machine.models.coding_submission import ProgrammingSubmission, ProgrammingTestCase, ProgrammingTestResult, SubmissionStatus
from machine.repositories import ExercisesRepository
from core.db import Transactional
from machine.repositories.programming_submission import ProgrammingSubmissionRepository
import machine.services.judge0_client as judge0_client
from core.logger import syslog
from tasks.update_submission_result import poll_judge0_submission_result

class SubmissionWithStats(TypedDict):
    submission: ProgrammingSubmission
    passed_testcases: int
    total_testcases: int

class ExercisesController(BaseController[Exercises]):
    def __init__(
        self,
        exercises_repository: ExercisesRepository,
        submission_repo: ProgrammingSubmissionRepository,
        llm_client: AsyncOpenAI
    ):
        super().__init__(
            model_class=Exercises, repository=exercises_repository
        )
        self.exercises_repository = exercises_repository
        self.submission_repo = submission_repo
        self.llm_client = llm_client

    @Transactional()
    async def get_coding_assistant_conversation_messages(
        self, user_id: UUID, coding_exercise_id: UUID
    ):
        # Retrieve the exercise record
        exercise = await self.repository.first(where_=[Exercises.id == coding_exercise_id])
        if not exercise:
            raise NotFoundException(message="Exercise not found.")
        
        session = self.repository.session

        # Ensure the exercise has an associated conversation
        if not getattr(exercise, "conversation_id", None):
            conversation = Conversation()
            session.add(conversation)
            # Flush to get an ID assigned to the new conversation
            await session.flush()
            exercise.conversation_id = conversation.id
        else:
            conversation = await session.get(Conversation, exercise.conversation_id)
            if not conversation:
                conversation = Conversation()
                session.add(conversation)
                await session.flush()
                exercise.conversation_id = conversation.id

        # Check for a coding conversation linking this user and conversation
        stmt = select(CodingConversation).where(
            CodingConversation.user_id == user_id,
            CodingConversation.conversation_id == conversation.id
        )
        result = await session.execute(stmt)
        coding_conv = result.scalars().first()

        if not coding_conv:
            # Create a new coding conversation if none exists
            coding_conv = CodingConversation(user_id=user_id, conversation_id=conversation.id)
            session.add(coding_conv)
            await session.flush()

        # Retrieve all messages for the conversation
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.created_at.asc())
        )
        result = await session.execute(stmt)
        messages = result.scalars().all()

        return messages

    @Transactional()
    async def push_coding_assistant_message(
        self, user_id: UUID, coding_exercise_id: UUID, content: str, role: str = "user"
    ):
        return await self._push_coding_assistant_message(
            user_id, coding_exercise_id, content, role
        )

    async def _push_coding_assistant_message(
        self, user_id: UUID, coding_exercise_id: UUID, content: str, role: str = "user"
    ):
        """
        Push a new message into the coding assistant conversation but not in transaction.
        
        Args:
            user_id (UUID): The ID of the user sending the message.
            coding_exercise_id (UUID): The ID of the coding exercise.
            content (str): The content of the message.
            role (str): The role of the sender (e.g., "user" or "assistant"). Default is "user".
            
        Returns:
            Message: The newly created message.
        """
        session = self.repository.session

        # Retrieve the exercise record
        exercise = await self.repository.first(where_=[Exercises.id == coding_exercise_id])
        if not exercise:
            raise NotFoundException(message="Exercise not found.")

        # Ensure the exercise has an associated conversation
        if not getattr(exercise, "conversation_id", None):
            conversation = Conversation()
            session.add(conversation)
            await session.flush()
            exercise.conversation_id = conversation.id
        else:
            conversation = await session.get(Conversation, exercise.conversation_id)
            if not conversation:
                conversation = Conversation()
                session.add(conversation)
                await session.flush()
                exercise.conversation_id = conversation.id

        # Ensure there is a coding conversation linking the user and the conversation
        stmt = select(CodingConversation).where(
            CodingConversation.user_id == user_id,
            CodingConversation.conversation_id == conversation.id
        )
        result = await session.execute(stmt)
        coding_conv = result.scalars().first()

        if not coding_conv:
            coding_conv = CodingConversation(user_id=user_id, conversation_id=conversation.id)
            session.add(coding_conv)
            await session.flush()

        # Create and add the new message to the conversation
        new_message = Message(
            role=role,
            content=content,
            conversation_id=conversation.id
        )
        session.add(new_message)
        await session.flush()  # Flush to assign an ID if needed

        return new_message

    async def invoke_coding_assistant(
        self,
        user_id: UUID,
        coding_exercise_id: UUID,
        content: str,
        user_solution: str,
        history_length=10
    ):
        """
        Invoke the Coding Assistant agent powered by LLM and stream the response.
        
        Steps:
        1. Push the user's message.
        2. Retrieve the last HISTORY_LENGTH messages from the conversation.
        3. Retrieve the problem description from the exercise record.
        4. Construct a system prompt with guardrails, incorporating the problem description
           and the user's solution.
        5. Invoke the LLM's Chat Completions API in streaming mode.
        6. Stream back the chunks while accumulating the full response.
        7. After streaming completes, persist the assistant's reply to the DB.
        
        Args:
            user_id (UUID): The ID of the user.
            coding_exercise_id (UUID): The ID of the coding exercise.
            content (str): The new user message.
            user_solution (str): The user's current work/solution attempt.
            
        Yields:
            Streaming response chunks.
        """
        # Push the user's new message.
        await self.push_coding_assistant_message(user_id, coding_exercise_id, content, role="user")

        # Retrieve the exercise record to get the problem description.
        exercise = await self.repository.first(where_=[Exercises.id == coding_exercise_id])
        problem_description = exercise.description if exercise and hasattr(exercise, "description") else "No description provided."

        # Retrieve conversation history.
        messages = await self.get_coding_assistant_conversation_messages(user_id, coding_exercise_id)
        # Keep only the last HISTORY_LENGTH messages.
        history = messages[-history_length:] if len(messages) > history_length else messages

        # Build the messages payload for the LLM.
        llm_messages = []
        # System prompt with educational guardrails and contextual information.
        system_prompt = (
            "You are an AI Coding Assistant designed for educational purposes. "
            "Your primary goal is to **support students in learning how to code**, not just solve problems for them.\n\n"

            "CONTEXT:\n"
            "- Problem Description: {problem_description}\n"
            "- User's Current Solution Attempt:\n{user_solution}\n\n"

            "RULES:\n"
            "1. Always explain concepts clearly and concisely.\n"
            "2. Use beginner-friendly language unless the context suggests advanced users.\n"
            "3. Guide the user through problem-solving steps, rather than giving full solutions outright.\n"
            "4. If the user's solution has issues, point them out **gently** and explain why they are incorrect.\n"
            "5. Never provide answers that are harmful, unsafe, or violate academic integrity policies.\n"
            "6. Keep your tone encouraging and educational.\n"
            "7. If you need to use code, keep it minimal and focus on the logic behind it.\n"

            "REQUIREMENTS:\n"
            "- Help the user reflect on their current approach.\n"
            "- Recommend improvements or corrections when applicable.\n"
            "- Offer small hints or suggestions rather than final answers unless explicitly asked.\n"
            "- Avoid distractions, off-topic comments, or excessive elaboration.\n"

            "Begin by analyzing the user's solution and assisting them with their current challenge."
        ).format(problem_description=problem_description, user_solution=user_solution)

        print("user_solution =", user_solution)

        llm_messages.append({"role": "system", "content": system_prompt})
        # Append the conversation history.
        for msg in history:
            llm_messages.append({"role": msg.role, "content": msg.content})
        # Optionally, add the current user message if it isn't already in history.
        if not history or history[-1].role != "user" or history[-1].content != content:
            llm_messages.append({"role": "user", "content": content})

        # Invoke the LLM via the Chat Completions API in streaming mode.
        response = await self.llm_client.chat.completions.create(
            model="gemini-2.0-flash",
            messages=llm_messages,
            stream=True,
        )

        assistant_reply = ""
        # Stream response chunks to the caller.
        async for chunk in response:
            # Extract the content delta (structure similar to OpenAI delta responses).
            delta = chunk.choices[0].delta
            content_chunk = delta.content

            if content_chunk is not None:
                assistant_reply += content_chunk
                yield content_chunk

        # Persist the assistant's full reply after streaming completes.
        await self.push_coding_assistant_message(user_id, coding_exercise_id, assistant_reply, role="assistant")

    @Transactional()
    async def create_coding_submission(
        self, user_id: UUID, exercise_id: UUID, judge0_lang_id: int, user_solution: str
    ) -> ProgrammingSubmission:
        """Submits a coding exercise solution and stores test result tokens.

        Args:
            user_id (UUID): The user ID.
            exercise_id (UUID): The coding exercise ID.
            judge0_lang_id (int): The language ID for Judge0.
            user_solution (str): The user's code.

        Returns:
            ProgrammingSubmission: The stored submission entry.
        """
        exercise = await self.repository.first(where_=[Exercises.id == exercise_id])
        if not exercise:
            raise NotFoundException(message=f"Exercise {exercise_id} not found.")

        session = self.repository.session
        stmt = select(ProgrammingTestCase).where(ProgrammingTestCase.exercise_id == exercise_id)
        result = await session.execute(stmt)
        test_case_objs = result.scalars().all()
        if not test_case_objs:
            raise NotFoundException(message="No test cases defined for this exercise.")

        test_cases = [{"input": tc.input, "expected": tc.expected_output} for tc in test_case_objs]
        test_results = await judge0_client.evaluate_test_cases(user_solution, judge0_lang_id, test_cases)

        submission_data = {
            "user_id": user_id,
            "exercise_id": exercise_id,
            "judge0_language_id": judge0_lang_id,
            "code": user_solution,
            "status": "pending",
            "score": None,
        }
        submission = await self.submission_repo.create(attributes=submission_data, commit=True)
        submission_status = SubmissionStatus.COMPLETED

        for i, tc in enumerate(test_case_objs):
            result_data = test_results[i]
            test_result = ProgrammingTestResult(
                submission_id=submission.id,
                testcase_id=tc.id,
                status=result_data["status"],
                stdout=result_data["stdout"],
                stderr=result_data["stderr"],
                judge0_token=result_data["token"],
                time=None,
                memory=None,
            )

            if result_data["status"] in ["In Queue", "Processing"]:
                submission_status = SubmissionStatus.PENDING
            elif result_data["status"] != "Accepted":
                submission_status = SubmissionStatus.FAILED

            session.add(test_result)

        submission.status = submission_status
        await session.flush()
        poll_judge0_submission_result.send(str(submission.id))
        return submission

    async def get_submission(
        self, submission_id: UUID, include_public_test_results: bool
    ):
        session = self.repository.session

        # Get the submission instance
        stmt = select(ProgrammingSubmission).where(
            ProgrammingSubmission.id == submission_id
        )
        
        if include_public_test_results:
            stmt = stmt.options(
                selectinload(ProgrammingSubmission.test_results),
                with_loader_criteria(ProgrammingTestResult, ProgrammingTestCase.is_public == True, include_aliases=True)
            )
        else:
            stmt = stmt.options(
                noload(ProgrammingSubmission.test_results)
            )

        stmt = stmt.order_by(ProgrammingSubmission.created_at.desc())
        result = await session.execute(stmt)
        submission = result.scalars().first()

        if not submission:
            raise NotFoundException(f"Submission {submission_id} not found")

        return submission

    async def list_submissions_with_stats(
        self, user_id: Optional[UUID] = None, exercise_id: Optional[UUID] = None
    ) -> list[SubmissionWithStats]:
        session = self.repository.session

        # Build base query for submissions
        stmt = select(ProgrammingSubmission)
        filters = []
        if user_id:
            filters.append(ProgrammingSubmission.user_id == user_id)
        if exercise_id:
            filters.append(ProgrammingSubmission.exercise_id == exercise_id)
        if filters:
            stmt = stmt.where(and_(*filters))

        result = await session.execute(stmt)
        submissions = result.scalars().all()
        if not submissions:
            return []

        submission_ids = [sub.id for sub in submissions]

        # Aggregate passed and total testcases per submission using GROUP BY
        stats_stmt = (
            select(
                ProgrammingTestResult.submission_id,
                func.count().label("total"),
                func.count(
                    func.nullif(
                        ProgrammingTestResult.status != "Accepted",
                        True
                    )
                ).label("passed")
            )
            .where(ProgrammingTestResult.submission_id.in_(submission_ids))
            .group_by(ProgrammingTestResult.submission_id)
        )

        stats_result = await session.execute(stats_stmt)
        stats_map = {row.submission_id: {"passed": row.passed, "total": row.total} for row in stats_result}

        # Combine stats with submissions
        response = []
        for sub in submissions:
            stats = stats_map.get(sub.id, {"passed": 0, "total": 0})
            response.append({
                "submission": sub,
                "passed_testcases": stats["passed"],
                "total_testcases": stats["total"]
            })

        return response


    @Transactional()
    async def get_submission_results(
        self, submission_id: UUID
    ) -> Sequence[ProgrammingTestResult]:
        """Polls Judge0 to update only test results still in 'Processing' state.

        Args:
            submission_id (UUID): ID of the submission.

        Returns:
            Sequence[ProgrammingTestResult]: All test results, with updated ones if applicable.
        """
        session = self.repository.session

        # Get all results for the submission
        stmt_all = select(ProgrammingTestResult).where(
            ProgrammingTestResult.submission_id == submission_id
        )
        result_all = await session.execute(stmt_all)
        all_results = result_all.scalars().all()
        if not all_results:
            raise NotFoundException(f"No test results found for submission {submission_id}")

        pending_results = [result.status == 'Processing' for result in result_all]
        if not pending_results:
            return all_results

        tokens = [tr.judge0_token for tr in pending_results if tr.judge0_token]
        if not tokens:
            return all_results

        test_cases: list[dict] = []
        for tr in pending_results:
            tc = await session.get(ProgrammingTestCase, tr.testcase_id)
            test_cases.append({"input": tc.input, "expected": tc.expected_output})

        judge0_results = await judge0_client.get_submission_results(tokens, test_cases)

        for tr, res in zip(pending_results, judge0_results):
            tr.status = res["status"]
            tr.stdout = res["stdout"]
            tr.stderr = res["stderr"]
            tr.time = None
            tr.memory = None

        await session.flush()
        return all_results

if __name__ == "__main__":
    import asyncio
    from uuid import UUID
    from machine.models import Exercises, ProgrammingSubmission
    from machine.repositories import ExercisesRepository
    from machine.repositories.programming_submission import ProgrammingSubmissionRepository
    from core.db.session import DB_MANAGER, Dialect
    from core.db.utils import session_context

    async def main() -> None:
        async with session_context(DB_MANAGER[Dialect.POSTGRES]) as session:
            exercises_repo = ExercisesRepository(db_session=session, model=Exercises)
            submission_repo = ProgrammingSubmissionRepository(db_session=session, model=ProgrammingSubmission)
            controller = ExercisesController(exercises_repo, submission_repo=submission_repo, llm_client=None)

            user_id = UUID("4dcc4c38-7615-4b02-9c89-4c4466c4314f")
            exercise_id = UUID("646cae67-e1c0-47db-b025-9b7da88693f5")

            user_solution = """# -*- coding: utf-8 -*-
def is_valid_parentheses(s):
    stack = []
    mapping = {')': '(', ']': '[', '}': '{'}

    for char in s:
        if char in mapping.values():
            stack.append(char)
        elif char in mapping:
            if not stack or stack[-1] != mapping[char]:
                return False
            stack.pop()
        else:
            continue

    return not stack

if __name__ == "__main__":
    import sys
    input_string = sys.stdin.read().strip()
    print(is_valid_parentheses(input_string))"""

            submission = await controller.create_coding_submission(
                user_id=user_id,
                exercise_id=exercise_id,
                judge0_lang_id=71,
                user_solution=user_solution.encode("utf-8", errors="ignore").decode("utf-8"),
            )

            syslog.info(f"Submission created with ID: {submission.id}")

            results = await controller.get_submission_results(submission.id)
            for r in results:
                syslog.info(f"Result: {r.status} | stdout: {r.stdout} | stderr: {r.stderr}")

            submissions_with_stats = await controller.list_submissions_with_stats(user_id=user_id)

            for item in submissions_with_stats:
                submission = item["submission"]
                passed = item["passed_testcases"]
                total = item["total_testcases"]
                print(f"Submission ID: {submission.id} | Passed: {passed}/{total} | Status: {submission.status}")


    asyncio.run(main())

