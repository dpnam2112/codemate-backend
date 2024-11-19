from fastapi import APIRouter, Depends
from machine.providers import InternalProvider
from machine.controllers.dashboard import DashboardController
from core.response import Ok
from core.exceptions import NotFoundException, BadRequestException
from machine.models import StudentCourses
from machine.schemas.responses.dashboard import WelcomeMessageResponse
from machine.schemas.requests import WelcomeMessageRequest

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/welcome", response_model=Ok[WelcomeMessageResponse])
async def get_welcome_message(
    request: WelcomeMessageRequest,
    dashboard_controller: DashboardController = Depends(InternalProvider().get_dashboard_controller),
):
    if not request.student_id:
        raise BadRequestException(message="Student ID is required.")

    recent_course = await dashboard_controller.student_courses_repository.first(
        where_=[StudentCourses.student_id == request.student_id],
        order_={"desc": [{"field": "last_accessed", "model_class": StudentCourses}]},
        relations=[StudentCourses.course]
    )

    if not recent_course:
        raise NotFoundException(message="No course found for the given student ID.")

    data = WelcomeMessageResponse(
        course=recent_course.course.name,
        course_id=recent_course.course.id,
        last_accessed=recent_course.last_accessed
    )
    return Ok(data=data, message="Successfully fetched the welcome message.")
