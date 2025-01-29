from sqlalchemy import and_
from machine.models import *
from core.response import Ok
from machine.controllers import *
from machine.schemas.requests import *
from typing import List, Union, Literal, Optional
from data.constant import expectedHeaders
from fastapi import APIRouter, Depends, Query
from machine.providers import InternalProvider
from core.utils.auth_utils import verify_token
from machine.schemas.responses.courses import *
from fastapi.security import OAuth2PasswordBearer
from core.exceptions import BadRequestException, NotFoundException, ForbiddenException
from core.utils.file import generate_presigned_url
from machine.schemas.responses.learning_path import LearningPathDTO, RecommendedLessonDTO


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
router = APIRouter(prefix="/courses", tags=["courses"])

@router.get("/student", response_model=Ok[GetCoursesPaginatedResponse])
async def get_student_courses(
    token: str = Depends(oauth2_scheme),
    search_query: Optional[str] = Query(None, description="Search query to filter courses"),
    student_courses_controller: StudentCoursesController = Depends(InternalProvider().get_studentcourses_controller),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
):

    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")

    student = await student_controller.student_repository.first(where_=[Student.id == user_id])
    if not student:
        raise NotFoundException(message="Your account is not allowed to access this feature.")
    if search_query:
        where_conditions = [StudentCourses.student_id == user_id, Courses.name.ilike(f"%{search_query}%")]
    else:
        where_conditions = [StudentCourses.student_id == user_id]
    select_fields = [
        Courses.id.label("id"),
        Courses.name.label("name"),
        Courses.start_date.label("start_date"),
        Courses.end_date.label("end_date"),
        Courses.learning_outcomes.label("learning_outcomes"),
        Courses.status.label("status"),
        Courses.image_url.label("image"),
        Courses.nCredit.label("nCredit"),
        Courses.nSemester.label("nSemester"),
        Courses.courseID.label("courseID"),
        StudentCourses.last_accessed.label("last_accessed"),
    ]

    join_conditions = {
        "courses": {"type": "left", "alias": "courses_alias"},
    }

    courses = await student_courses_controller.student_courses_repository._get_many(
        where_=where_conditions,
        fields=select_fields,
        join_=join_conditions,
        order_={"asc": ["last_accessed"]},
        limit=10,
        skip=0,
    )

    if not courses:
        return Ok(data=[], message="No courses found.")

    total_page = int(len(courses) / 10)

    courses_response = {
        "content": [
            GetCoursesResponse(
                id=course.id,
                name=course.name,
                start_date=str(course.start_date),
                end_date=str(course.end_date),
                learning_outcomes=course.learning_outcomes or [],
                status=course.status,
                image=str(course.image),
                last_accessed=str(course.last_accessed),
                nCredit=course.nCredit,
                nSemester=course.nSemester,
                courseID=course.courseID,
            )
            for course in courses
        ],
        "pageSize": 10,
        "currentPage": 1,
        "totalRows": len(courses),
        "totalPages": total_page,
    }

    return Ok(data=courses_response, message="Successfully fetched the courses.")


@router.get("/{courseId}", response_model=Ok[GetCourseDetailResponse])
async def get_course_for_student(
    courseId: str,
    token: str = Depends(oauth2_scheme),
    student_courses_controller: StudentCoursesController = Depends(InternalProvider().get_studentcourses_controller),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
):
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")

    student = await student_controller.student_repository.first(where_=[Student.id == user_id])
    if not student:
        raise NotFoundException(message="Your account is not allowed to access this feature.")

    select_fields = [
        Courses.name.label("name"),
        Courses.id.label("id"),
        Courses.start_date.label("start_date"),
        Courses.end_date.label("end_date"),
        Courses.learning_outcomes.label("learning_outcomes"),
        Courses.status.label("status"),
        Courses.image_url.label("image"),
        Courses.nCredit.label("nCredit"),
        Courses.nSemester.label("nSemester"),
        Courses.courseID.label("courseID"),
        StudentCourses.last_accessed.label("last_accessed"),
        StudentCourses.completed_lessons.label("completed_lessons"),
        StudentCourses.time_spent.label("time_spent"),
        StudentCourses.assignments_done.label("assignments_done"),
    ]

    join_conditions = {
        "courses": {"type": "left", "alias": "courses_alias"},
    }

    course = await student_courses_controller.student_courses_repository._get_many(
        where_=[and_(StudentCourses.course_id == courseId, StudentCourses.student_id == user_id)],
        fields=select_fields,
        join_=join_conditions,
    )
    get_course = course[0] if course else None
    if not course:
        course_response = GetCourseDetailResponse(
            course_id=courseId,
            course_name="",
            course_start_date="",
            course_end_date="",
            course_learning_outcomes=[],
            course_status="",
            course_image="",
            course_percentage_complete="",
            course_last_accessed="",
            completed_lessons=0,
            time_spent="",
            assignments_done=0,
        )
        return Ok(data=course_response, message="You are not enrolled in this course.")

    course_response = GetCourseDetailResponse(
        course_id=str(courseId),
        course_name=get_course.name,
        course_start_date=str(get_course.start_date) if get_course.start_date else "",
        course_end_date=str(get_course.end_date) if get_course.end_date else "",
        course_learning_outcomes=get_course.learning_outcomes or [],
        course_status=get_course.status,
        course_image=str(get_course.image) if get_course.image else "",
        course_percentage_complete="",
        course_last_accessed=str(get_course.last_accessed) if get_course.last_accessed else "",
        completed_lessons=get_course.completed_lessons or 0,
        time_spent=str(get_course.time_spent) if get_course.time_spent else "",
        assignments_done=get_course.assignments_done or 0,
    )

    return Ok(data=course_response, message="Successfully fetched the course.")


@router.get("/{courseId}/professor", response_model=Ok[ProfessorInformation])
async def get_professor_for_course(
    courseId: str,
    token: str = Depends(oauth2_scheme),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
    courses_controller: CoursesController = Depends(InternalProvider().get_courses_controller),
):
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")

    course = await courses_controller.courses_repository.first(where_=[Courses.id == courseId])
    if not course:
        raise NotFoundException(message="Course not found.")

    professor = await professor_controller.professor_repository.first(where_=[Professor.id == course.professor_id])
    if not professor:
        raise NotFoundException(message="Professor not found.")

    professor_response = ProfessorInformation(
        professor_id=professor.id,
        professor_name=professor.name,
        professor_email=professor.email,
        professor_avatar=str(professor.avatar_url) if professor.avatar_url else "",
    )
    return Ok(data=professor_response, message="Successfully fetched the professor.")


@router.get("/{courseId}/students", response_model=Ok[List[StudentList]])
async def get_students_for_course(
    courseId: str,
    token: str = Depends(oauth2_scheme),
    student_courses_controller: StudentCoursesController = Depends(InternalProvider().get_studentcourses_controller),
):
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")

    select_fields = [
        Student.id.label("id"),
        Student.name.label("name"),
        Student.email.label("email"),
        Student.avatar_url.label("avatar_url"),
    ]

    join_conditions = {
        "student": {"type": "left", "table": Student},
    }

    students = await student_courses_controller.student_courses_repository._get_many(
        where_=[StudentCourses.course_id == courseId],
        fields=select_fields,
        join_=join_conditions,
    )

    if not students:
        return Ok(data=[], message="No students found.")

    students_response = [
        StudentList(
            student_id=student.id,
            student_name=student.name,
            student_email=student.email,
            student_avatar=str(student.avatar_url) if student.avatar_url else "",
        )
        for student in students
    ]

    return Ok(data=students_response, message="Successfully fetched the students.")

@router.get("/{courseId}/lessons", response_model=Ok[List[GetLessonsResponse]])
async def get_lessons_for_course(
    courseId: str,
    token: str = Depends(oauth2_scheme),
    lessons_controller: LessonsController = Depends(InternalProvider().get_lessons_controller),
):
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")

    select_fields = [
        Lessons.id.label("id"),
        Lessons.title.label("title"),
        Lessons.description.label("description"),
        Lessons.learning_outcomes.label("learning_outcomes"),
        Lessons.order.label("order"),
    ]

    lessons = await lessons_controller.lessons_repository._get_many(
        where_=[Lessons.course_id == courseId],
        fields=select_fields,
    )

    if not lessons:
        return Ok(data=[], message="No lessons found.")

    lessons_response = [
        GetLessonsResponse(
            id=lesson.id,
            title=lesson.title,
            description=lesson.description or "",
            learning_outcomes=lesson.learning_outcomes or [],
            order=lesson.order,
        )
        for lesson in lessons
    ]

    return Ok(data=lessons_response, message="Successfully fetched the lessons.")


@router.get(
    "/{courseId}/lessons_recommendation/",
    response_model=Ok[List[GetLessonsRecommendationResponse]],
)
async def get_lessons_recommendation(
    courseId: UUID,
    token: str = Depends(oauth2_scheme),
    learning_paths_controller: LearningPathsController = Depends(InternalProvider().get_learningpaths_controller),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
    lessons_controller: LessonsController = Depends(InternalProvider().get_lessons_controller),
):
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")

    student = await student_controller.student_repository.first(where_=[Student.id == user_id])
    if not student:
        raise NotFoundException(message="Your account is not allowed to access this feature.")

    where_learning_path_conditions = [
        LearningPaths.student_id == user_id,
        LearningPaths.course_id == courseId,
    ]
    learning_path = await learning_paths_controller.learning_paths_repository.first(
        where_=where_learning_path_conditions,
        relations=[LearningPaths.recommend_lessons, LearningPaths.course],
    )

    if not learning_path:
        raise NotFoundException(message="Learning path not found for the given student and course.")

    recommend_lessons = learning_path.recommend_lessons
    course_name = learning_path.course.name if learning_path.course else "Unknown Course"

    if not recommend_lessons:
        raise NotFoundException(message="No recommended lessons found for the given learning path.")

    recommended_lessons: List[GetLessonsRecommendationResponse] = []
    for recommend_lesson in recommend_lessons:
        lesson = await lessons_controller.lessons_repository.first(where_=[Lessons.id == recommend_lesson.id])
        if not lesson:
            continue

        recommended_lessons.append(
            GetLessonsRecommendationResponse(
                course_id=courseId,
                course_name=course_name,
                lesson_id=lesson.id,
                title=lesson.title,
                description=lesson.description or "",
                order=lesson.order,
                bookmark=lesson.bookmark if hasattr(lesson, "bookmark") else False,
                status=recommend_lesson.status,
            )
        )

    return Ok(data=recommended_lessons, message="Successfully fetched the recommended lessons.")


@router.post("/", response_model=Ok[Union[CreateCourseResponse, List[CreateCourseResponse]]])
async def create_course(
    request: CreateCourseRequest,
    token: str = Depends(oauth2_scheme),
    courses_controller: CoursesController = Depends(InternalProvider().get_courses_controller),
    professors_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
    student_courses_controller: StudentCoursesController = Depends(InternalProvider().get_studentcourses_controller),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
    admin_controller: AdminController = Depends(InternalProvider().get_admin_controller),
):
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")

    user = await admin_controller.admin_repository.first(where_=[Admin.id == user_id])
    if not user:
        raise NotFoundException(message="Your account is not allowed to create a course.")

    if not request.headers or not request.courses:
        raise BadRequestException(message="Headers and Courses are required.")

    if not request.headers == expectedHeaders:
        raise BadRequestException(message="Headers must match the fixed values: {expectedHeaders}")

    if len(request.courses) == 0:
        raise BadRequestException(message="At least one course is required.")

    if len(request.courses) == 1:
        saveProfessorId = await professors_controller.professor_repository.first(
            Professor.email == request.courses[0].professor_email
        )
        saveProfessorId = saveProfessorId.id
        course_attributes = {
            "name": request.courses[0].name,
            "professor_id": saveProfessorId,
            "nCredit": request.courses[0].nCredit,
            "nSemester": request.courses[0].nSemester,
            "createdByAdminID": user_id,
            "courseID": request.courses[0].courseID,
        }

        createCourse = await courses_controller.courses_repository.create(attributes=course_attributes, commit=True)
        if not createCourse:
            raise Exception("Failed to create course")

        getStudentIDs = await student_controller.student_repository._get_many(
            where_=Student.email.in_([student for student in request.courses[0].student_list]), fields=[Student.id]
        )

        student_courses_attributes = [
            {
                "student_id": student.id,
                "course_id": createCourse.id,
            }
            for student in getStudentIDs
        ]

        create_student_courses = await student_courses_controller.student_courses_repository.create_many(
            attributes_list=student_courses_attributes, commit=True
        )

        if not create_student_courses:
            print("Failed to create student courses")
            raise Exception("Failed to create student courses")

        student_courses_response = [
            {
                "student_id": create_student_courses.id,
                "course_id": createCourse.id,
                "last_accessed": str(create_student_courses.last_accessed),
                "completed_lessons": create_student_courses.completed_lessons,
                "time_spent": str(create_student_courses.time_spent),
                "assignments_done": create_student_courses.assignments_done,
            }
        ]

        course_response = {
            "course_id": createCourse.id,
            "courseID": createCourse.courseID,
            "name": createCourse.name,
            "professor_id": createCourse.professor_id,
            "start_date": str(createCourse.start_date),
            "end_date": str(createCourse.end_date),
            "status": createCourse.status,
            "nCredit": createCourse.nCredit,
            "nSemester": createCourse.nSemester,
            "learning_outcomes": createCourse.learning_outcomes if createCourse.learning_outcomes else "",
            "image_url": str(createCourse.image_url),
            "student_courses_list": student_courses_response,
        }
        return Ok(data=course_response, message="Successfully created the course.")
    else:
        professor_emails = [course.professor_email for course in request.courses]
        professors = await professors_controller.professor_repository._get_many(
            where_=[Professor.email.in_(professor_emails)], fields=[Professor.id, Professor.email]
        )

        professor_id_map = {prof["email"]: prof["id"] for prof in professors}

        courses_attributes = []
        for course in request.courses:
            if not course.name:
                raise BadRequestException(message="Course name is required.")

            professor_id = professor_id_map.get(course.professor_email)
            if not professor_id:
                raise NotFoundException(message=f"Professor with email {course.professor_email} not found")

            course_attr = {
                "name": course.name,
                "professor_id": professor_id,
                "nCredit": course.nCredit,
                "nSemester": course.nSemester,
                "createdByAdminID": user_id,
                "status": "new",
                "courseID": course.courseID,
            }
            # if hasattr(course, 'start_date') and course.start_date:
            #     course_attr["start_date"] = course.start_date
            # if hasattr(course, 'end_date') and course.end_date:
            #     course_attr["end_date"] = course.end_date
            # if hasattr(course, 'image_url') and course.image_url:
            #     course_attr["image_url"] = course.image_url

            courses_attributes.append(course_attr)

        create_courses = await courses_controller.courses_repository.create_many(
            attributes_list=courses_attributes, commit=True
        )
        if not create_courses:
            raise Exception("Failed to create courses")

        courses_response = []
        for created_course, request_course in zip(create_courses, request.courses):

            student_emails = request_course.student_list
            students = await student_controller.student_repository._get_many(
                where_=[Student.email.in_(student_emails)], fields=[Student.id, Student.email]
            )

            student_courses_attributes = [
                {
                    "student_id": student["id"],
                    "course_id": created_course.id,
                }
                for student in students
            ]

            create_student_courses = await student_courses_controller.student_courses_repository.create_many(
                attributes_list=student_courses_attributes, commit=True
            )

            if not create_student_courses:
                raise Exception("Failed to create student courses")

            student_courses_response = [
                {
                    "student_id": sc.student_id,
                    "course_id": sc.course_id,
                    "last_accessed": str(sc.last_accessed),
                    "completed_lessons": sc.completed_lessons,
                    "time_spent": str(sc.time_spent),
                    "assignments_done": sc.assignments_done,
                }
                for sc in create_student_courses
            ]

            course_response = {
                "course_id": created_course.id,
                "courseID": created_course.courseID,
                "name": created_course.name,
                "professor_id": created_course.professor_id,
                "start_date": str(created_course.start_date) if created_course.start_date else "",
                "end_date": str(created_course.end_date) if created_course.end_date else "",
                "status": created_course.status,
                "nCredit": created_course.nCredit,
                "nSemester": created_course.nSemester,
                "learning_outcomes": created_course.learning_outcomes if created_course.learning_outcomes else "",
                "image_url": str(created_course.image_url) if created_course.image_url else "",
                "student_courses_list": student_courses_response,
            }
            courses_response.append(course_response)

        return Ok(data=courses_response, message="Successfully created the courses.")

@router.get("/{course_id}/personalized-lp", response_model=Ok[LearningPathDTO])
async def get_personalized_lp(
    course_id: UUID,
    token: str = Depends(oauth2_scheme),
    lp_controller: LearningPathsController = Depends(InternalProvider().get_learningpaths_controller),
):
    payload = verify_token(token)
    student_id = payload.get("sub")
    if not student_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    lp = await lp_controller.get_learning_path(course_id=course_id, user_id=student_id)

    return Ok(data=LearningPathDTO.model_validate(lp))


@router.get(
    "/{course_id}/learning-path/recommended-lessons",
    response_model=Ok[List[RecommendedLessonDTO]],
)
async def get_recommended_lessons(
    course_id: UUID,
    token: str = Depends(oauth2_scheme),
    expand: Optional[Literal["modules"]] = Query(None, description="Expand related data, e.g., 'modules'."),
    lp_controller: LearningPathsController = Depends(InternalProvider().get_learningpaths_controller),
):
    payload = verify_token(token)
    student_id = payload.get("sub")
    if not student_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    recommended_lessons = await lp_controller.get_recommended_lessons(
        user_id=student_id, course_id=course_id, expand=expand
    )

    return Ok(data=recommended_lessons)


@router.delete("/{course_id}/learning-path")
async def delete_learning_path(
    course_id: UUID,
    token: str = Depends(oauth2_scheme),
    lp_controller: LearningPathsController = Depends(InternalProvider().get_learningpaths_controller),
):
    payload = verify_token(token)
    student_id = payload.get("sub")
    if not student_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    await lp_controller.delete_learning_path(user_id=student_id, course_id=course_id)
    return Ok(data=None, message="Successfully deleted the learning path.")
