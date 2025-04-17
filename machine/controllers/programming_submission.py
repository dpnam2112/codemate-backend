from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import noload
from core.controller.base import BaseController
from machine.models.coding_submission import ProgrammingSubmission, ProgrammingTestResult, SubmissionStatus
from machine.services.code_exercise_assistant import CodeExerciseAssistantService
from machine.schemas.programming_submission import LLMEvaluation
from machine.models.exercises import Exercises
from machine.repositories import ExercisesRepository

class ProgrammingSubmissionController(BaseController[ProgrammingSubmission]):
    def __init__(self, *args, exercise_repository: ExercisesRepository, code_exercise_assistant_service: CodeExerciseAssistantService, **kwargs):
        super().__init__(*args, **kwargs)
        self.exercise_repository = exercise_repository
        self.assistant_service = code_exercise_assistant_service

    async def get_submission_status(self, submission_id: UUID) -> SubmissionStatus:
        """
        Get the status of a programming submission by its ID.
        
        Args:
            submission_id (UUID): The ID of the programming submission.
        
        Returns:
            str: The status of the programming submission.
        """
        # Fetch the submission from the database
        submission = await self.repository.first(
            where_=[ProgrammingSubmission.id == submission_id]
        )
        
        # Check if the submission exists
        if not submission:
            raise ValueError(f"Submission with ID {submission_id} not found.")
        
        return submission.status

    async def get_submission_with_stat(self, submission_id: UUID) -> Optional[dict]:
        session = self.repository.session

        # Fetch the submission by ID
        stmt = select(ProgrammingSubmission).where(ProgrammingSubmission.id == submission_id)
        stmt = stmt.options(noload(ProgrammingSubmission.test_results))
        result = await session.execute(stmt)
        submission = result.scalar_one_or_none()

        if not submission:
            return None

        # Fetch test result stats for this submission
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
            .where(ProgrammingTestResult.submission_id == submission_id)
            .group_by(ProgrammingTestResult.submission_id)
        )

        stats_result = await session.execute(stats_stmt)
        stats_row = stats_result.one_or_none()

        stats = {
            "passed": stats_row.passed if stats_row else 0,
            "total": stats_row.total if stats_row else 0
        }

        return {
            "submission": submission,
            "passed_testcases": stats["passed"],
            "total_testcases": stats["total"]
        }

    async def evaluate_submission(self, submission_id: UUID) -> Optional[LLMEvaluation]:
        """
        Evaluate a submission using LLM.
        
        Args:
            submission_id (UUID): The ID of the submission to evaluate
            
        Returns:
            Optional[LLMEvaluation]: The evaluation result
        """
        # Fetch the submission with test results
        submission = await self.repository.first(
            where_=[ProgrammingSubmission.id == submission_id],
            options_=[noload(ProgrammingSubmission.test_results)]
        )
        
        if not submission:
            raise ValueError(f"Submission with ID {submission_id} not found.")
            
        # Get test results
        test_results = [{
            "status": tr.status,
            "stdout": tr.stdout,
            "stderr": tr.stderr
        } for tr in submission.test_results]
        
        problem_description = await self._get_problem_description(submission.exercise_id)
        
        # Evaluate the submission
        evaluation = await self.assistant_service.evaluate_submission(
            code=submission.code,
            problem_description=problem_description,
            language_id=submission.judge0_language_id,
            test_results=test_results
        )
        
        if evaluation:
            # Update the submission with evaluation
            submission.llm_evaluation = evaluation.model_dump()
            self.repository.session.add(submission)
            
        return evaluation

    async def _get_problem_description(self, exercise_id: UUID) -> str:
        """
        Get the problem description for an exercise.
        
        Args:
            exercise_id (UUID): The ID of the exercise
            
        Returns:
            str: The problem description, or a default message if not found
        """
        # Fetch the exercise using the exercise repository
        exercise = await self.exercise_repository.first(
            where_=[Exercises.id == exercise_id]
        )
        
        if not exercise:
            return "Problem description not available"
            
        # Return the description if it exists, otherwise return a default message
        return exercise.description or "No description provided"
