import logging
from typing import List
from core.response import Ok
from machine.models import *
from datetime import datetime
from pydantic import ValidationError
from machine.schemas.requests import *
from machine.controllers import *
from machine.providers import InternalProvider
from machine.schemas.responses.dashboard import *
from fastapi import APIRouter, Depends, HTTPException
from core.exceptions import NotFoundException, BadRequestException
from fastapi.security import OAuth2PasswordBearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
from core.utils.auth_utils import verify_token
router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/student-welcome", response_model=Ok[WelcomeMessageResponse])
async def get_welcome_message(
    token: str = Depends(oauth2_scheme),
    studentcourses_controller: StudentCoursesController = Depends(InternalProvider().get_studentcourses_controller),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller)
):
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")

    student = await student_controller.student_repository.first(
        where_=[Student.id == user_id],
    )
    
    if not student:
        raise NotFoundException(message="You are not a student. Please log in as a student to access this feature.")
    
    recent_course = await studentcourses_controller.student_courses_repository.first(
        where_=[StudentCourses.student_id == user_id],
        order_={"desc": [{"field": "last_accessed", "model_class": StudentCourses}]},
        relations=[StudentCourses.course],
    )

    if not recent_course:
        raise NotFoundException(message="No course found for the given student ID.")

    data = WelcomeMessageResponse(
        course=recent_course.course.name, course_id=recent_course.course.id, last_accessed=recent_course.last_accessed
    )
    return Ok(data=data, message="Successfully fetched the welcome message.")

@router.get("/student-activities", response_model=Ok[List[GetRecentActivitiesResponse]])
async def get_activities(
    token: str = Depends(oauth2_scheme),
    activities_controller: ActivitiesController = Depends(InternalProvider().get_activities_controller),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller)
):
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    
    student = await student_controller.student_repository.first(
        where_=[Student.id == user_id],
    )
    
    if not student:
        raise NotFoundException(message="You are not a student. Please log in as a student to access this feature.")


    recent_activities = await activities_controller.activities_repository.get_many(
        where_=[Activities.student_id == user_id],
        order_={"desc": [{"field": "timestamp", "model_class": Activities}]},
        limit=5,
        skip=0,
    )

    # if not recent_activities:
    #     student_exists = await activities_controller.activities_repository.get_many(
    #         where_=[Activities.student_id == user_id]
    #     )
    #     if not student_exists:
    #         raise NotFoundException(message="Student ID not found in the database.")

    #     raise NotFoundException(message="No activities found for the given student ID.")

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


@router.post("/student-activities/", response_model=Ok[bool])
async def add_activity(
    request: AddActivityRequest,
    token: str = Depends(oauth2_scheme),
    activities_controller: ActivitiesController = Depends(InternalProvider().get_activities_controller),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller)
):
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    
    student = await student_controller.student_repository.first(
        where_=[Student.id == user_id],
    )
    
    if not student:
        raise NotFoundException(message="You are not a student. Please log in as a student to access this feature.")


    try:
        if not request.type or not request.description:
            raise BadRequestException(message="Student ID, activity type, and activity description are required.")

        activity = await activities_controller.activities_repository.create(
            attributes={
                "student_id": user_id,
                "type": request.type,
                "description": request.description,
                "timestamp": datetime.now(),
            },
            commit=True,
        )

        if not activity:
            raise NotFoundException(message="Failed to add activity.")

        return Ok(data=True, message="Successfully added the activity.")
    except ValidationError as e:
        raise HTTPException(status_code=500, detail=f"Validation error: {e.errors()}")
