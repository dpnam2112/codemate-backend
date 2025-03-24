
from typing import List
from core.response import Ok
from machine.models import *
from datetime import datetime
from machine.controllers import *
from pydantic import ValidationError
from machine.schemas.requests import *
from machine.controllers import *
from machine.providers import InternalProvider
from machine.schemas.responses.dashboard import *
from fastapi.security import OAuth2PasswordBearer
from fastapi import APIRouter, Depends, HTTPException
from core.exceptions import NotFoundException, BadRequestException
from core.utils.auth_utils import verify_token
import datetime
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
router = APIRouter(prefix="/schedule", tags=["schedule"])
@router.get("/events", response_model=Ok[List[Events]])
async def get_all_events(
    token: str = Depends(oauth2_scheme),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
    courses_controller: CoursesController = Depends(InternalProvider().get_courses_controller),
    student_courses_controller: StudentCoursesController = Depends(InternalProvider().get_studentcourses_controller),
    exercises_controller: ExercisesController = Depends(InternalProvider().get_exercises_controller),
):

    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")

    # Check if the user is a professor
    professor = await professor_controller.professor_repository.first(
        where_=[Professor.id == user_id]
    )
    
    # Check if the user is a student
    student = await student_controller.student_repository.first(
        where_=[Student.id == user_id]
    )
    
    if not professor and not student:
        raise NotFoundException(message="User not found as either professor or student.")
    
    courses = []
    
    # If user is a professor, get all courses they teach
    if professor:
        courses = await courses_controller.courses_repository.get_many(
            where_=[Courses.professor_id == user_id]
        )
    
    # If user is a student, get all courses they are enrolled in
    elif student:
        student_courses = await student_courses_controller.student_courses_repository.get_many(
            where_=[StudentCourses.student_id == user_id]
        )
        
        # Get the course for each student-course relationship
        for sc in student_courses:
            course = await courses_controller.courses_repository.first(
                where_=[Courses.id == sc.course_id]
            )
            if course:
                courses.append(course)
    
    # Get all upcoming exercises for the courses
    upcoming_exercises_list = []
    current_time = datetime.datetime.utcnow()
    
    for course in courses:
        upcoming_exercises = await exercises_controller.exercises_repository.get_many(
            where_=[
                Exercises.course_id == course.id,
            ]
        )
        
        for exercise in upcoming_exercises:
            upcoming_exercises_list.append({
                "exercise": exercise,
                "course": course
            })
    
    # Sort exercises by time_close (closest deadline first)
    upcoming_exercises_list = sorted(upcoming_exercises_list, key=lambda item: item["exercise"].time_close)
    
    # Map exercises to Events response model
    events = []
    for item in upcoming_exercises_list:
        exercise = item["exercise"]
        course = item["course"]
        
        events.append(
            Events(
                exercise_id=exercise.id,
                exercise_name=exercise.name,
                exercise_time_open=exercise.time_open,
                exercise_time_close=exercise.time_close,
                exercise_type=exercise.type,
                course_name=course.name,
                course_id=course.id,
                course_courseID=course.courseID,
                course_nSemester=course.nSemester
            )
        )
    
    return Ok(data=events, message="Successfully fetched all upcoming exercise events.")