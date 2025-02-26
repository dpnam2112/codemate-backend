from sqlalchemy import and_, extract
from machine.models import *
from core.response import Ok
from machine.controllers import *
from machine.schemas.requests.feedback import *
from machine.schemas.responses.feedback import *
from typing import List
from fastapi import APIRouter, Depends, Query
from machine.providers import InternalProvider
from core.utils.auth_utils import verify_token
from machine.schemas.responses.courses import *
from fastapi.security import OAuth2PasswordBearer
from core.exceptions import *
from machine.schemas.responses.learning_path import LearningPathDTO, RecommendedLessonDTO
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
router = APIRouter(prefix="/feedback", tags=["feedback"])

@router.post("/")
async def create_feedback(
    request: CreateFeedbackRequest,
    token: str = Depends(oauth2_scheme),
    feedback_controller: FeedbackController = Depends(InternalProvider().get_feedback_controller),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
):
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")

    student = await student_controller.student_repository.first(where_=[Student.id == user_id])
    professor = await professor_controller.professor_repository.first(where_=[Professor.id == user_id])
    
    if not student and not professor:
        raise BadRequestException(message="You are not allowed to create feedback.")

    user_type = "student" if student else "professor"
    
    feedback_attributes = {
        "feedback_type": request.type,
        "title": request.title,
        "category": request.category,
        "description": request.description,
        "rate": request.rate,
        "status": "pending",
        "course_id": request.course_id,
        "student_id": user_id if user_type == "student" else None,
        "professor_id": user_id if user_type == "professor" else None,
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
                student_mssv=student.mssv,
            )
        )

    return Ok(data=feedback_response)



@router.get("/") #, response_model=Ok[List[GetFeedbackListResponse]])
async def get_feedback_list(
    month: int = Query(None, ge=1, le=12), 
    year: int = Query(None),
    feedback_type: str = Query(None, title="Feedback Type", description="Type of feedback", example="system"), 
    status: str = Query(None, title="Feedback Status", description="Status of feedback", example="pending"),
    category: str = Query(None, title="Feedback Category", description="Category of feedback", example="user_interface"),
    token: str = Depends(oauth2_scheme),
    feedback_controller: FeedbackController = Depends(InternalProvider().get_feedback_controller),
    admin_controller: AdminController = Depends(InternalProvider().get_admin_controller),
):
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")

    is_admin = await admin_controller.admin_repository.exists(where_=[Admin.id == user_id])
    if not is_admin:
        raise ForbiddenException(message="You are not allowed to get feedbacks.")

    filters = [] 
    
    if category:
        if category not in ["user_interface", "feature_request", "bug_report", "performance", "others"]:
            raise BadRequestException(message="Invalid feedback category. Please provide a valid feedback category.")
        filters.append(Feedback.category == category)
        
    if feedback_type:
        if feedback_type not in ["system", "course"]:
            raise BadRequestException(message="Invalid feedback type. Please provide a valid feedback type.")
        filters.append(Feedback.feedback_type == feedback_type)
        
    if status:
        if status not in ["pending", "in_progress", "resolved"]:
            raise BadRequestException(message="Invalid feedback status. Please provide a valid feedback status.")
        filters.append(Feedback.status == status)
        
    if month:
        filters.append(extract('month', Feedback.created_at) == month)  
    if year:
        filters.append(extract('year', Feedback.created_at) == year) 
        
    join_conditions = {
        "student": {"type": "left", "alias": "student_alias"},
    }
    
    select_fields = [
        Feedback.id,
        Feedback.feedback_type,
        Feedback.title,
        Feedback.category,
        Feedback.description,
        Feedback.rate,
        Feedback.status,
        Feedback.created_at,
        Feedback.resolved_at,
        Feedback.student_id,
        Student.name.label("name"),
        Student.email.label("email"),
    ]

    feedbacks = await feedback_controller.feedback_repository._get_many(where_=filters, join_=join_conditions, fields=select_fields)
    feedback_response = [
        {"id": feedback.id,
        "type": feedback.feedback_type,
        "title": feedback.title,
        "category": feedback.category,
        "description": feedback.description,
        "rate": feedback.rate,
        "status": feedback.status,
        "created_at": feedback.created_at,
        "resolved_at": feedback.resolved_at if feedback.resolved_at else "",
        "student_id": feedback.student_id,
        "student_name": feedback.name if feedback.name else "",
        "student_email": feedback.email if feedback.email else "",}
        for feedback in feedbacks
    ]
    # feedback_response = []
    # for feedback in feedbacks:
    #     feedback_response.append(
    #         GetFeedbackListResponse(
    #             id=str(feedback.id),  
    #             type=feedback.feedback_type,
    #             title=feedback.title,
    #             category=feedback.category,
    #             description=feedback.description,
    #             rate=feedback.rate,
    #             status=feedback.status,
    #             created_at=str(feedback.created_at),
    #             resolved_at=str(feedback.resolved_at) if feedback.resolved_at else "",
    #             student_id=str(feedback.student_id),  
    #             student_name=feedback.name if feedback.name else "",
    #             student_email=feedback.email if feedback.email else "",
    #         )
    #     )
    
    return Ok(data=feedback_response, message="Feedbacks retrieved successfully.")