from pydantic import BaseModel
from uuid import UUID


class LPPlanningResponse(BaseModel):
    learning_path_id: UUID
    message: str

