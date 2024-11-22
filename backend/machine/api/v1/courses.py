from fastapi import APIRouter, Depends
from sqlalchemy.sql import func, and_
from typing import List
from machine.models import *
from machine.schemas.responses.courses import *
from machine.schemas.requests import *
from core.response import Ok
from core.exceptions import BadRequestException
from machine.providers import InternalProvider
from machine.controllers import *
from core.repository.enum import UserRole
from sqlalchemy.orm import aliased

router = APIRouter(prefix="/courses", tags=["courses"])

@router.get("/", response_model=Ok[GetCoursesPaginatedResponse])
async def get_courses(
    request: GetCoursesRequest,
    courses_controller: CoursesController = Depends(InternalProvider().get_courses_controller),
):
    if not request.student_id:
        raise BadRequestException(message="Student ID is required.")

    ProfessorUser = aliased(User)
    StudentUser = aliased(User)

    where_conditions = [StudentCourses.student_id == request.student_id, User.role == UserRole.student]

    join_conditions = {
        "student_courses": {"type": "left", "alias": "student_courses"},
        "professor": {"type": "left", "table": ProfessorUser, "alias": "professor_alias"},
        "lessons": {"type": "left", "alias": "lessons_alias"},
        "student": {"type": "left", "table": StudentUser, "alias": "student_alias"},
    }
    
    select_fields = [
        Courses.id.label("course_id"),
        Courses.name.label("course_name"),
        Courses.start_date,
        Courses.end_date,
        Courses.learning_outcomes,
        Courses.status.label("course_status"),
        Courses.image_url.label("course_image"),
        StudentCourses.last_accessed,
        func.count(Lessons.id).label("total_lessons"),
        StudentCourses.completed_lessons.label("completed_lessons"),
        ProfessorUser.id.label("professor_id"), 
        ProfessorUser.name.label("professor_name"),
        ProfessorUser.email.label("professor_email"),
        StudentUser.name.label("student_name"),
        StudentUser.email.label("student_email"),
    ]


    group_by_fields = [
        Courses.id,
        ProfessorUser.id,
        StudentUser.id,
        StudentCourses.completed_lessons,
        StudentCourses.last_accessed,
    ]

    order_conditions = {"asc": ["start_date"]}


    paginated_courses = await courses_controller.courses_repository._get_many(
        skip=request.offset,
        limit=request.page_size,
        fields=select_fields,
        where_=where_conditions,
        join_=join_conditions,
        group_by_=group_by_fields,
        order_=order_conditions,
    )


    total_rows = await courses_controller.courses_repository.count(where_=where_conditions)
    total_pages = (total_rows + request.page_size - 1) // request.page_size

    content: List[GetCoursesResponse] = []
    for course in paginated_courses:
        content.append(
            GetCoursesResponse(
                id=course.course_id,
                name=course.course_name,
                start_date=str(course.start_date),
                end_date=str(course.end_date),
                learning_outcomes=course.learning_outcomes,
                status=course.course_status,
                image=str(course.course_image),
                percentage_complete= f"{(course.completed_lessons/course.total_lessons*100) if course.total_lessons > 0 else 0:.0f}",
                last_accessed=course.last_accessed.isoformat() if course.last_accessed else None,
                professor=ProfessorInformation(
                    professor_id=course.professor_id,
                    professor_name=course.professor_name,
                    professor_email=course.professor_email,
                ),
                student_list=[
                    StudentList(
                        student_id=request.student_id,
                        student_name=course.student_name or "",
                        student_email=course.student_email or "",
                    )
                ],
            )
        )

    return Ok(
        GetCoursesPaginatedResponse(
            content=content,
            currentPage=(request.offset // request.page_size) + 1,
            pageSize=request.page_size,
            totalRows=total_rows,
            totalPages=total_pages,
        )
    )
    
@router.get("/{courseId}/students/{studentId}/", response_model=Ok[GetCourseDetailResponse])
async def get_course_for_student(
    courseId: str, 
    studentId: str, 
    student_courses_controller: StudentCoursesController = Depends(InternalProvider().get_studentcourses_controller),
    courses_controller: CoursesController = Depends(InternalProvider().get_courses_controller),
    lessons_controller: LessonsController = Depends(InternalProvider().get_lessons_controller),
    exercises_controller: ExercisesController = Depends(InternalProvider().get_exercises_controller),
):
    course_id = courseId
    student_id = studentId
    if not course_id or not student_id:
        raise BadRequestException(message="Student ID and Course ID are required.")

    # Validate if student is enrolled in the course
    student_course = await student_courses_controller.student_courses_repository.first(
        where_=[
            and_(StudentCourses.student_id == student_id, StudentCourses.course_id == course_id)
        ]
    )
    if not student_course:
        raise BadRequestException(message="Student is not enrolled in this course.")

    # Fetch lessons for the course
    lessons = await lessons_controller.lessons_repository.get_many(
        where_=[
            Lessons.course_id == course_id,
            Lessons.lesson_type == "original",
        ],
        order_={"asc": ["order"]},
    )

    # Fetch exercises for the lessons
    lesson_ids = [lesson.id for lesson in lessons]
    exercises = await exercises_controller.exercises_repository.get_many(
        where_=[
            and_(Exercises.lesson_id.in_(lesson_ids), Exercises.type == "original")
        ]
    )

    # Group exercises by lesson_id
    exercises_by_lesson = {}
    for exercise in exercises:
        exercises_by_lesson.setdefault(exercise.lesson_id, []).append(exercise)

    # Transform lessons with their respective exercises
    lessons_response: List[GetLessonsResponse] = []
    for lesson in lessons:
        lesson_exercises = exercises_by_lesson.get(lesson.id, [])
        lessons_response.append(
            GetLessonsResponse(
                id=lesson.id,
                title=lesson.title,
                description=str(lesson.description),
                lesson_type=lesson.lesson_type,
                bookmark=lesson.bookmark,
                order=lesson.order,
                status=lesson.status,
                exercises=[
                    GetExercisesResponse(
                        id=exercise.id,
                        name=exercise.name,
                        description=str(exercise.description),
                        status=exercise.status,
                        type=exercise.type,
                    )
                    for exercise in lesson_exercises
                ],
            )
        )

    # Construct and return the response
    response = GetCourseDetailResponse(
        course_id=student_course.course_id,
        student_id=student_course.student_id,
        completed_lessons=student_course.completed_lessons,
        time_spent=str(student_course.time_spent),
        assignments_done=student_course.assignments_done,
        lessons=lessons_response,
    )
    return Ok(data=response, message="Successfully fetched the course details.")