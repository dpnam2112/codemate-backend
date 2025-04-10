from uuid import UUID
from core.controller.base import BaseController
from machine.models.coding_submission import ProgrammingSubmission, SubmissionStatus

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
