from fastapi import APIRouter, Depends, Query

from machine.providers import InternalProvider
from machine.controllers.dashboard import DashboardController
from core.response import Ok
from core.exceptions import NotFoundException, BadRequestException
from machine.models import StudentCourses

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/welcome")
async def get_welcome_message(
    student_id: str = Query(..., description="The ID of the student to get the welcome message for"),
    dashboard_controller: DashboardController = Depends(InternalProvider().get_dashboard_controller),
):
    if not student_id:
        raise BadRequestException(message="Student ID is required")

    recent_course = await dashboard_controller.student_courses_repository.first(
        where_=[StudentCourses.student_id == student_id],
        order_={"desc": [{"field": "last_accessed", "model_class": StudentCourses}]},
        relations=[StudentCourses.course]
    )

    if not recent_course:
        raise NotFoundException(message="No recent course found for this student")

    return Ok(data={
        "message": f"Welcome! Your most recent course is {recent_course.course.name}.",
        "course": recent_course.course.name,
        "course_id": str(recent_course.course.id),
        "last_accessed": recent_course.last_accessed
    })