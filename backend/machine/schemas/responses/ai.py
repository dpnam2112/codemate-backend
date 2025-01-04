from pydantic import BaseModel
from uuid import UUID


class RecommendLearningResourcesResponse(BaseModel):
    """
    Schema for the response of the recommend learning resources endpoint.
    """
    learning_path_id: UUID
    message: str

