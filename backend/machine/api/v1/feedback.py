from sqlalchemy import and_
from machine.models import *
from core.response import Ok
from machine.controllers import *
from machine.schemas.requests.feedback import *
from machine.schemas.responses.feedback import *
from typing import List, Union, Literal, Optional
from data.constant import expectedHeaders
from fastapi import APIRouter, Depends, Query
from machine.providers import InternalProvider
from core.utils.auth_utils import verify_token
from machine.schemas.responses.courses import *
from fastapi.security import OAuth2PasswordBearer
from core.exceptions import BadRequestException, NotFoundException
from machine.schemas.responses.learning_path import LearningPathDTO, RecommendedLessonDTO

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
router = APIRouter(prefix="/feedback", tags=["feedback"])

@router.post("/")
async def create_feedback(
    request: CreateFeedbackRequest,
    token: str = Depends(oauth2_scheme),
    feedback_controller: FeedbackController = Depends(InternalProvider().get_feedback_controller),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
):
    # Token validation
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")

    # Student existence check
    student = await student_controller.student_repository.first(where_=Student.id == user_id)
    if not student:
        raise BadRequestException(message="You are not allowed to create feedback.")

    # Feedback creation
    feedback_attributes = {
        "feedback_type": request.type,
        "title": request.title,
        "category": request.category,
        "description": request.description,
        "rate": request.rate,
        "status": "pending",
        "student_id": user_id,
    }

    try:
        feedback = await feedback_controller.feedback_repository.create(
            attributes=feedback_attributes, 
            commit=True
        )
    except Exception as e:
        raise BadRequestException(message=f"Failed to create feedback: {str(e)}")

    feedback_response = CreateFeedbackResponse(
        id=str(feedback.id),
        type=feedback.feedback_type,
        title=feedback.title,
        category=feedback.category,
        description=feedback.description,
        rate=feedback.rate,
        status=feedback.status,
        created_at=str(feedback.created_at),
        resolved_at=str(feedback.resolved_at) if feedback.resolved_at else "",
    )
    
    return Ok(data=feedback_response, message="Feedback created successfully.")