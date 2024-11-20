from fastapi import APIRouter, Depends
from machine.providers import InternalProvider
from machine.controllers.dashboard import *
from core.response import Ok
from core.exceptions import NotFoundException, BadRequestException
from machine.models import *
from machine.schemas.responses.dashboard import *
from machine.schemas.requests import *
from typing import List

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
        relations=[StudentCourses.course],
    )

    if not recent_course:
        raise NotFoundException(message="No course found for the given student ID.")

    data = WelcomeMessageResponse(
        course=recent_course.course.name, course_id=recent_course.course.id, last_accessed=recent_course.last_accessed
    )
    return Ok(data=data, message="Successfully fetched the welcome message.")


@router.get("/activities", response_model=Ok[List[GetRecentActivitiesResponse]])
async def get_activities(
    request: GetRecentActivitiesRequest,
    activities_controller: ActivitiesController = Depends(InternalProvider().get_activities_controller),
):
    if not request.student_id:
        raise BadRequestException(message="Student ID is required.")

    recent_activities = await activities_controller.activities_repository.get_many(
        where_=[Activities.student_id == request.student_id],
        order_={"desc": [{"field": "timestamp", "model_class": Activities}]},
        limit=request.limit,
        skip=request.offset,
    )

    if not recent_activities:
        student_exists = await activities_controller.activities_repository.get_many(
            where_=[Activities.student_id == request.student_id]
        )
        if not student_exists:
            raise NotFoundException(message="Student ID not found in the database.")

        raise NotFoundException(message="No activities found for the given student ID.")

    activities_data = [
        GetRecentActivitiesResponse(
            activity_id=activity.id,
            activity_description=activity.description,
            activity_type=activity.type,
            activity_date=activity.timestamp,
        )
        for activity in recent_activities
    ]

    return Ok(data=activities_data, message="Successfully fetched the recent activities.")

