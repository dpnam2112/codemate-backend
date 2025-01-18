from typing import List
from core.response import Ok
from machine.models import *
from fastapi import APIRouter, Depends
from machine.schemas.requests import *
from machine.schemas.responses.progress_tracking import *
from machine.controllers import *
from machine.providers import InternalProvider
from core.exceptions import NotFoundException, BadRequestException
import uuid
from fastapi.security import OAuth2PasswordBearer
from core.utils.auth_utils import verify_token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
router = APIRouter(prefix="/teacher_progress_tracking", tags=["teacher_progress_tracking"])

@router.get("/courses", response_model=Ok[GetCoursesListResponse])
async def get_courses(
    token: str = Depends(oauth2_scheme),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
    courses_controller: CoursesController = Depends(InternalProvider().get_courses_controller),
):
    """
    Get the list of courses
    """
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    
    user = await professor_controller.professor_repository.first(where_=[Professor.id == user_id])
    
    if not user:  
        raise NotFoundException(message="Only professors have the permission to create lesson.")
    
    courses = await courses_controller.courses_repository.get_many(
        where_=[Courses.professor_id == user_id]
    )
    if not courses:
        raise NotFoundException(message="No courses found.")
    course_name_list = [
        CourseNameResponse(course_id=course.id, course_name=course.name)
        for course in courses
    ]
    return Ok(data=GetCoursesListResponse(course_name_list=course_name_list), message="Successfully fetched the course list.")
@router.get("/courses/{course_id}/exercises", response_model=Ok[GetExercisesListResponse])
async def get_courses(
    course_id: UUID,
    token: str = Depends(oauth2_scheme),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
    courses_controller: CoursesController = Depends(InternalProvider().get_courses_controller),
):
    """
    Get the list of courses
    """
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    
    user = await professor_controller.professor_repository.first(where_=[Professor.id == user_id])
    
    if not user:  
        raise NotFoundException(message="Only professors have the permission to create lesson.")
    
    courses = await courses_controller.courses_repository.first(
        where_=[Courses.id == course_id],
        relations=[Courses.exercises]
    )
    if not courses:
        raise NotFoundException(message="No courses found.")
    exercises_name_list =[]
    if courses.exercises:
        exercises_name_list = [
            ExerciseNameResponse(exercise_id=exercise.id, exercise_name=exercise.name)
            for exercise in courses.exercises
        ]

    return Ok(data=GetExercisesListResponse(exercises_name_list=exercises_name_list), message="Successfully fetched the course list.")
