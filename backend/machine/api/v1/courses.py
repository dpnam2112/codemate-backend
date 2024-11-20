from fastapi import APIRouter, Depends
from machine.repositories import CoursesRepository
from machine.models import StudentCourses
from machine.schemas.responses.courses import *
from machine.schemas.requests import GetCoursesRequest
from core.response import Ok
from core.exceptions import BadRequestException, NotFoundException
from machine.providers import InternalProvider
from machine.controllers import CoursesController
router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("/", response_model=Ok[GetCoursesPaginatedResponse])
async def get_courses(
    request: GetCoursesRequest,
    courses_controller: CoursesController = Depends(InternalProvider().get_courses_controller),
):
    if not request.student_id:
        raise BadRequestException(message="Student ID is required.")

    # Fetch student courses with pagination
    student_courses = await courses_controller.courses_repository.get_many(
        where_=[StudentCourses.student_id == request.student_id],
        order_={"desc": [{"field": "last_accessed", "model_class": StudentCourses}]},  # Order by last accessed
        limit=request.page_size,
    )

    if not student_courses:
        raise NotFoundException(message="No courses found for this student.")

    courses_data = []
    total_courses = await courses_controller.courses_repository.count(
        where_=[StudentCourses.student_id == request.student_id]
    )  

    for student_course in student_courses:
        course = student_course
        total_lessons = len(course.lessons)
        completed_lessons = student_course.completed_lessons
        percentage_complete = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0

        last_accessed = student_course.last_accessed.strftime("%Y-%m-%d %H:%M:%S")

        courses_data.append(
            GetCoursesResponse(
                id=course.id,
                name=course.name,
                start_date=course.start_date.strftime("%Y-%m-%d") if course.start_date else "",
                end_date=course.end_date.strftime("%Y-%m-%d") if course.end_date else "",
                student_list=[
                    StudentList(student_id=student.id, student_name=student.name, student_email=student.email)
                    for student in course.students
                ],
                learning_outcomes=course.learning_outcomes or [],
                professor_id=course.professor_id,
                status=course.status,
                image=course.image_url,
                percentage_complete=str(round(percentage_complete, 2)),
                last_accessed=last_accessed,
            )
        )

    total_pages = (total_courses // request.page_size) + (1 if total_courses % request.page_size else 0)

    response_data = GetCoursesPaginatedResponse(
    content=courses_data,
    currentPage=(request.offset // request.page_size) + 1,
    pageSize=request.page_size,
    totalRows=total_courses,
    totalPages=total_pages,
)
    return Ok(data=response_data, message="Successfully fetched the courses.")
