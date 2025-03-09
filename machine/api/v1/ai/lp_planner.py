from typing import Annotated
from fastapi import APIRouter, Depends
from machine.api.tags import APITag
from machine.controllers.ai.lp_planning import LPPPlanningController
from machine.providers.internal import InternalProvider
from machine.schemas.requests.v1.ai import LearningPathPlanningRequest
from core.response import Ok
from machine.schemas.responses.ai import LPPlanningResponse

router = APIRouter(prefix="/lp-planner", tags=[APITag.AI])

@router.post(":invoke", response_model=Ok[LPPlanningResponse])
async def invoke_lp_planner(
    body: LearningPathPlanningRequest,
    controller: Annotated[LPPPlanningController, Depends(InternalProvider().get_lp_planning_controller)]
):
    learning_path, llm_response = await controller.invoke_lp_planner(
        user_id=body.user_id,
        course_id=body.course_id,
        goal=body.goal,
    )

    return Ok(
        data=LPPlanningResponse(
            learning_path_id=learning_path["id"],
            llm_response=llm_response,
            message="Learning path and recommendations created successfully."
        )
    )

