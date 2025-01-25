
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
router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/student-recent-course", response_model=Ok[WelcomeMessageResponse])
async def get_recent_course(
    token: str = Depends(oauth2_scheme),
    studentcourses_controller: StudentCoursesController = Depends(InternalProvider().get_studentcourses_controller),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
):
    """
    Get the most recently accessed course by the student.
    """
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
    return Ok(data=data, message="Successfully fetched the recent course.")


@router.get("/student-activities", response_model=Ok[List[GetRecentActivitiesResponse]])
async def get_activities(
    token: str = Depends(oauth2_scheme),
    activities_controller: ActivitiesController = Depends(InternalProvider().get_activities_controller),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
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


@router.post("/student-activities", response_model=Ok[bool])
async def add_activity(
    request: AddActivityRequest,
    token: str = Depends(oauth2_scheme),
    activities_controller: ActivitiesController = Depends(InternalProvider().get_activities_controller),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
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

@router.get("/professors", response_model=Ok[GetDashboardProfessorResponse])
async def get_professor_dashboard(
    token: str = Depends(oauth2_scheme), 
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
    courses_controller: CoursesController = Depends(InternalProvider().get_courses_controller),
    lessons_controller: LessonsController = Depends(InternalProvider().get_lessons_controller),
    student_courses_controller: StudentCoursesController = Depends(InternalProvider().get_studentcourses_controller),
    exercises_controller: ExercisesController = Depends(InternalProvider().get_exercises_controller),
):
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")

    professor = await professor_controller.professor_repository.first(where_=[Professor.id == user_id])

    if not professor:
        raise NotFoundException(message="Only professors have the permission to get professor dashboard.")
    
    n_courses = await courses_controller.courses_repository.count(where_=[Courses.professor_id == professor.id])
    courses = await courses_controller.courses_repository.get_many(where_=[Courses.professor_id == professor.id])

    n_lessons = 0
    n_students_set = set()
    n_exercises = 0
    for course in courses:
        lessons_count = await lessons_controller.lessons_repository.count(where_=[Lessons.course_id == course.id])
        n_lessons += lessons_count

        student_courses = await student_courses_controller.student_courses_repository.get_many(
            where_=[StudentCourses.course_id == course.id]
        )
        student_ids = [sc.student_id for sc in student_courses]  # Chỉ lấy ID sinh viên
        n_students_set.update(student_ids)  # Thêm vào set để loại bỏ trùng lặp
        
        exercises_count = await exercises_controller.exercises_repository.count(where_=[Exercises.course_id == course.id])
        n_exercises += exercises_count

    upcoming_exercises_list = []
    current_time = datetime.datetime.utcnow()

    for course in courses:
        upcoming_exercises = await exercises_controller.exercises_repository.get_many(
            where_=[
                Exercises.course_id == course.id,
                Exercises.deadline > current_time
            ],
        )
        upcoming_exercises_list.extend(upcoming_exercises)

    upcoming_exercises_list = sorted(upcoming_exercises_list, key=lambda ex: ex.deadline)[:5]
    upcoming_events = [
        Events(
            exercise_id=exercise.id,
            exercise_name=exercise.name,
            exercise_deadline=exercise.deadline,
        )
        for exercise in upcoming_exercises_list
    ]

    response = GetDashboardProfessorResponse(
        professor_id=professor.id,
        professor_name=professor.name,
        nCourses=n_courses,
        nLessons=n_lessons,
        nStudents=len(n_students_set),
        nExercises=n_exercises,
        upcoming_events=upcoming_events
    )

    return Ok(data=response, message="Successfully fetched professor dashboard.")
