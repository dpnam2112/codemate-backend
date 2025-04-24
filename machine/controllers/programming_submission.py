from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import noload
from core.controller.base import BaseController
from machine.models.coding_submission import ProgrammingSubmission, ProgrammingTestResult, SubmissionStatus

class ProgrammingSubmissionController(BaseController[ProgrammingSubmission]):
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
