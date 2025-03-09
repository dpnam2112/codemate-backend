from pydantic import BaseModel
from uuid import UUID

from machine.services.workflows.tools import LPPlanningWorkflowResponse


class LPPlanningResponse(BaseModel):
    learning_path_id: UUID
    llm_response: LPPlanningWorkflowResponse
    message: str

