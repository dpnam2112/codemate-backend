from typing import Annotated
from fastapi import APIRouter, Depends
from machine.api.tags import APITag
from machine.controllers.ai.recommender import AIRecommenderController
from machine.providers.internal import InternalProvider
from machine.schemas.requests.v1.ai import RecommendLearningResourcesRequest
from core.response import Ok
from machine.schemas.responses.ai import RecommendLearningResourcesResponse

router = APIRouter(prefix="/recommender", tags=[APITag.AI])

@router.post(":invoke", response_model=Ok[RecommendLearningResourcesResponse])
async def recommend_learning_resources(
    body: RecommendLearningResourcesRequest,
    controller: Annotated[AIRecommenderController, Depends(InternalProvider().get_ai_recommender_controller)]
):
    """
    Endpoint for generating personalized learning resource recommendations.

    Args:
        body (RecommendLearningResourcesRequest): Request body containing user ID, course ID, and learning goal.
        controller (AIRecommenderController): The AI recommender controller dependency.

    Returns:
        Ok[RecommendLearningResourcesResponse]: A response containing the learning path ID and a success message.
    """
    learning_path = await controller.recommend_lessons(
        user_id=body.user_id,
        course_id=body.course_id,
        goal=body.goal,
    )

    return Ok(
        data=RecommendLearningResourcesResponse(
            learning_path_id=learning_path.id,
            message="Learning path and recommendations created successfully."
        )
    )

