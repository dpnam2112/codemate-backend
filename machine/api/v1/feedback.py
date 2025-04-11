from sqlalchemy import and_, extract
from machine.models import *
from core.response import Ok
from machine.controllers import *
from machine.schemas.requests.feedback import *
from machine.schemas.responses.feedback import *
from typing import List, Union
from fastapi import APIRouter, Depends, Query
from machine.providers import InternalProvider
from core.utils.auth_utils import verify_token
from machine.schemas.responses.courses import *
from fastapi.security import OAuth2PasswordBearer
from core.exceptions import *
from datetime import datetime, timezone, timedelta
from core.repository.enum import FeedbackStatusType
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
router = APIRouter(prefix="/feedback", tags=["feedback"])

from typing import Union
from fastapi import Depends
from pydantic import BaseModel

@router.post("/")
async def create_feedback(
    request: Union[CreateFeedbackRequest, CreateFeedbackCourseRequest],
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
        "feedback_type": "course" if request.type == "course" else "system",  # Fixed here
        "title": request.title,
        "category": request.category,
        "description": request.description,
        "rate": request.rate,
        "status": "pending",
        "student_id": user_id if user_type == "student" else None,
        "professor_id": user_id if user_type == "professor" else None,
        "course_id": request.course_id if request.type == "course" else None,
    }

    if isinstance(request, CreateFeedbackCourseRequest):
        if not request.course_id:
            raise BadRequestException(message="Course ID is required for course feedback.")
        feedback_attributes["course_id"] = request.course_id

    try:
        feedback = await feedback_controller.feedback_repository.create(
            attributes=feedback_attributes, 
            commit=True
        )
    except Exception as e:
        raise BadRequestException(message=f"Failed to create feedback: {str(e)}")

    feedback_response = CreateFeedbackResponse(
        id=str(feedback.id),
        type=feedback.feedback_type,  # Now works as expected
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



from datetime import date

@router.get("/", description="Get all feedbacks")
async def get_feedback_list(
    month: int = Query(None, ge=1, le=12), 
    year: int = Query(None),
    feedback_type: str = Query(None, title="Feedback Type", description="Type of feedback", example="system"), 
    status: str = Query(None, title="Feedback Status", description="Status of feedback", example="pending"),
    category: str = Query(None, title="Feedback Category", description="Category of feedback", example="user_interface"),
    start_date: date = Query(None, description="Start date for feedback creation (format: YYYY-MM-DD)"),
    end_date: date = Query(None, description="End date for feedback creation (format: YYYY-MM-DD)"),
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
    
    # Handle the start_date and end_date for the created_at range filter
    if start_date:
        filters.append(Feedback.created_at >= start_date)  # Greater than or equal to the start date
    if end_date:
        filters.append(Feedback.created_at <= end_date)  # Less than or equal to the end date

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
        "type": "course" if feedback.feedback_type == "course" else "system",
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

@router.patch("/{feedback_id}")
async def update_feedback(
    feedback_id: str,
    request: UpdateFeedbackRequest,
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
        raise ForbiddenException(message="You are not allowed to update feedbacks.")

    feedback = await feedback_controller.feedback_repository.first(where_=[Feedback.id == feedback_id])
    if not feedback:
        raise BadRequestException(message="Feedback not found.")

    # Log the status and resolved_at values for debugging
    print(f"Updating feedback with ID={feedback_id}: Status={request.status}, Resolved At={datetime.now(timezone(timedelta(hours=7))) if request.status == FeedbackStatusType.resolved else None}")
    
    try:
        # Handle timezone-naive datetime for resolved_at
        resolved_at = datetime.now(timezone(timedelta(hours=7))).replace(tzinfo=None) if request.status == FeedbackStatusType.resolved else None
        
        updated_feedback = await feedback_controller.feedback_repository.update(
            where_=[Feedback.id == feedback_id],
            attributes={
                "status": request.status,
                "resolved_at": resolved_at,  # Ensure it's timezone-naive
            },
            commit=True,
        )
        
        if not updated_feedback:
            raise BadRequestException(message="Failed to update feedback.")
        
        return Ok(data=bool(True), message="Feedback updated successfully.")

    except Exception as e:
        print(f"Error updating feedback: {str(e)}")
        raise BadRequestException(message=f"Failed to update feedback: {str(e)}")   
@router.delete("/{feedback_id}")
async def delete_feedback(
    feedback_id: str,
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
        raise ForbiddenException(message="You are not allowed to delete feedbacks.")

    feedback = await feedback_controller.feedback_repository.first(where_=[Feedback.id == feedback_id])
    if not feedback:
        raise BadRequestException(message="Feedback not found.")

    try:
        await feedback_controller.feedback_repository.delete(where_=[Feedback.id == feedback_id])
        await feedback_controller.feedback_repository.session.commit()
    except Exception as e:
        raise BadRequestException(message=f"Failed to delete feedback: {str(e)}")

    return Ok(data=bool(True), message="Feedback deleted successfully.")