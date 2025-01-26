from sqlalchemy import and_
from machine.models import *
from core.response import Ok
from machine.controllers import *
from machine.schemas.requests.feedback import *
from machine.schemas.responses.feedback import *
from typing import List
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

@router.get("/courses/{course_id}", response_model=Ok[List[GetFeedbackProfessorResponse]])
async def get_feedback_professor(
    course_id: str,
    token: str = Depends(oauth2_scheme),
    feedback_controller: FeedbackController = Depends(InternalProvider().get_feedback_controller),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
    courses_controller: CoursesController = Depends(InternalProvider().get_courses_controller),
):
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")

    professor = await professor_controller.professor_repository.first(where_=[Professor.id == user_id])
    if not professor:
        raise BadRequestException(message="You are not allowed to get feedbacks.")

    course = await courses_controller.courses_repository.first(
        where_=[
            Courses.id == course_id,
            Courses.professor_id == professor.id
        ]
    )
    if not course:
        raise BadRequestException(message="Course not found.")

    feedbacks = await feedback_controller.feedback_repository.get_many(
        where_=[Feedback.course_id == course_id]
    )
        
    feedback_response = []
    for feedback in feedbacks:
        student = await student_controller.student_repository.first(where_=[Student.id == feedback.student_id])
        if not student:
            raise BadRequestException(message=f"Student not found for feedback ID: {feedback.id}")
        
        feedback_response.append(
            GetFeedbackProfessorResponse(
                id=feedback.id,
                type=feedback.feedback_type,
                title=feedback.title,
                category=feedback.category,
                description=feedback.description,
                rate=feedback.rate,
                status=feedback.status,
                created_at=str(feedback.created_at),
                resolved_at=str(feedback.resolved_at) if feedback.resolved_at else "",
                student_id=feedback.student_id,
                student_name=student.name,
                student_email=student.email,
            )
        )

    return Ok(data=feedback_response)