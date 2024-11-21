from fastapi import APIRouter, Depends
from sqlalchemy.sql import func, case
from typing import List
from machine.models import Courses, StudentCourses, Lessons, User
from machine.schemas.responses.courses import (
    GetCoursesPaginatedResponse,
    GetCoursesResponse,
    StudentList,
    ProfessorInformation,
)
from machine.schemas.requests import GetCoursesRequest
from core.response import Ok
from core.exceptions import BadRequestException
from machine.providers import InternalProvider
from machine.controllers.courses import CoursesController
from sqlalchemy.types import Float
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
        StudentCourses.completed_lessons,
        (
            case(
                (
                    func.count(Lessons.id) > 0,
                    func.cast(
                        (func.cast(StudentCourses.completed_lessons, Float) / func.cast(func.count(Lessons.id), Float))
                        * 100,
                        Float,
                    ),
                ),
                else_=0.0,
            )
        ).label("percentage_complete"),
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
                percentage_complete=f"{course.percentage_complete:.2f}%",
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
