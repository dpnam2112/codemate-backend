from machine.models import *
from core.response import Ok
from machine.controllers import *
from machine.schemas.requests import *
from fastapi import APIRouter, Depends, Query
from machine.providers import InternalProvider
from core.utils.auth_utils import verify_token
from machine.schemas.responses.courses import *
from fastapi.security import OAuth2PasswordBearer
from core.exceptions import BadRequestException, NotFoundException, ForbiddenException
from core.utils.file import generate_presigned_url 
from sqlalchemy import or_
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
router = APIRouter(prefix="/professors", tags=["professors"])

@router.get("/courses", response_model=Ok[GetProfessorCoursesPaginatedResponse])
async def get_professor_courses(
    token: str = Depends(oauth2_scheme),
    page: int = Query(1, description="Page number"),
    page_size: int = Query(10, description="Number of items per page"),
    search_query: Optional[str] = Query(None, description="Search query to filter courses"),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
    courses_controller: CoursesController = Depends(InternalProvider().get_courses_controller),
    student_courses_controller: StudentCoursesController = Depends(InternalProvider().get_studentcourses_controller),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
):
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    
    professor = await professor_controller.professor_repository.first(where_=[Professor.id == user_id])
    if not professor:
        raise NotFoundException(message="Your account is not allowed to get professor courses list.")
    
    where_conditions = [Courses.professor_id == professor.id]
    
    if search_query:
        where_conditions.append(
            or_(
                Courses.name.ilike(f"%{search_query}%"),
                Courses.class_name.ilike(f"%{search_query}%"),
                Courses.courseID.ilike(f"%{search_query}%"),
            )
        )
    
    # Fetch courses with pagination and filtering
    courses = await courses_controller.courses_repository.get_many(
        where_=where_conditions,
        order_={"desc": ["start_date"]},
        limit=page_size,
        skip=(page - 1) * page_size,
    )

    # If no courses are found
    if not courses:
        return Ok(data=GetProfessorCoursesPaginatedResponse(content=[], currentPage=page, pageSize=page_size, totalRows=0, totalPages=0), message="No courses found.")


    courses_response = []
    for course in courses:
        student_courses = await student_courses_controller.student_courses_repository.get_many(
            where_=[StudentCourses.course_id == course.id]
        )
        student_ids = [sc.student_id for sc in student_courses]

        students = await student_controller.student_repository.get_many(
            where_=[Student.id.in_(student_ids)]  
        )

        student_list = [
            StudentList(
                student_id=student.id,
                student_name=student.name,
                student_email=student.email,
                student_avatar=str(student.avatar_url),
            )
            for student in students
        ]

        learning_outcomes = course.learning_outcomes if course.learning_outcomes is not None else []

        course_data = GetProfessorCoursesResponse(
            id=course.id,
            name=course.name,
            start_date=course.start_date,
            end_date=course.end_date,
            student_list=student_list,
            learning_outcomes=learning_outcomes,
            professor=ProfessorInformation(
                professor_id=professor.id,
                professor_name=professor.name,
                professor_email=professor.email,
                professor_avatar=professor.avatar_url if professor.avatar_url else "",
            ),
            status=course.status,
            image_url=generate_presigned_url(course.image_url, expiration=604800) if course.image_url else "",
            nSemester=course.nSemester,
            nCredit=course.nCredit,
            courseID=course.courseID,
            class_name=str(course.class_name),
        )

        courses_response.append(course_data)

    total_rows = len(courses_response)
    total_pages = (total_rows + page_size - 1) // page_size

    paginated_content = courses_response[(page - 1) * page_size : page * page_size]

    response = GetProfessorCoursesPaginatedResponse(
        content=paginated_content,
        currentPage=page,
        pageSize=page_size,
        totalRows=total_rows,
        totalPages=total_pages,
    )

    return Ok(data=response, message="Successfully fetched professor courses.")

@router.get("/courses/{course_id}", response_model=Ok[GetCourseDetailProfessorResponse])
async def get_course_detail_for_professor(
    course_id: UUID,
    token: str = Depends(oauth2_scheme),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
    courses_controller: CoursesController = Depends(InternalProvider().get_courses_controller),
    student_courses_controller: StudentCoursesController = Depends(InternalProvider().get_studentcourses_controller),
    lessons_controller: LessonsController = Depends(InternalProvider().get_lessons_controller),
    exercises_controller: ExercisesController = Depends(InternalProvider().get_exercises_controller),
    document_controller: DocumentsController = Depends(InternalProvider().get_documents_controller),
):
    # Verify token
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    
    # Check professor
    professor = await professor_controller.professor_repository.first(
        where_=[Professor.id == user_id]
    )
    if not professor:
        raise NotFoundException(message="Your account is not allowed to get professor courses detail.")

    # Get course
    course = await courses_controller.courses_repository.first(
        where_=[Courses.id == course_id]
    )
    if not course:
        raise NotFoundException(message="Course not found.")

    if course.professor_id != professor.id:
        raise ForbiddenException(message="You are not authorized to access this course details.")

    student_courses = await student_courses_controller.student_courses_repository.get_many(
            where_=[StudentCourses.course_id == course.id]
        )
    exercises_count = await exercises_controller.exercises_repository.count(where_=[Exercises.course_id == course.id])
    lessons = await lessons_controller.lessons_repository.get_many(
        where_=[Lessons.course_id == course_id]
    )
    
    documents_count = 0
    for lesson in lessons:
        doc_count = await document_controller.documents_repository.count(
            where_=[Documents.lesson_id == lesson.id]
        )
        documents_count += doc_count
    image_url = ""
    if course.image_url:
        image_url = generate_presigned_url(course.image_url, expiration=604800)
    course_detail = GetCourseDetailProfessorResponse(
        course_id=course.id,
        course_name=course.name,
        course_start_date=course.start_date.isoformat(),
        course_end_date=course.end_date.isoformat(),
        course_learning_outcomes=course.learning_outcomes or [],
        course_status=course.status,
        course_image_url=image_url,
        course_nCredit=course.nCredit,
        course_nSemester=course.nSemester,
        course_courseID=course.courseID,
        course_class_name=course.class_name,
        nStudents=len(student_courses),
        nLessons=len(lessons),
        nExercises=exercises_count,
        nDocuments=documents_count
    )

    return Ok[GetCourseDetailProfessorResponse](data=course_detail)
@router.put("/courses/{course_id}/learning_outcomes", response_model=Ok[PutLearningOutcomesCoursesResponse])
async def change_learning_outcomes(
    course_id: UUID,
    body: PutLearningOutcomesCoursesRequest,
    token: str = Depends(oauth2_scheme),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
    courses_controller: CoursesController = Depends(InternalProvider().get_courses_controller),
):
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")

    user = await professor_controller.professor_repository.first(where_=[Professor.id == user_id])
    if not user:
        raise NotFoundException(message="Your account is not allowed to update course's learning outcomes.")

    course = await courses_controller.courses_repository.first(
        where_=[
            Courses.id == course_id,
        ]
    )

    if not course:
        raise BadRequestException(message="Course not found.")

    if user.id != course.professor_id:
        raise BadRequestException(message="You are not allowed to update this course's learning outcomes.")

    learning_outcomes = body.learning_outcomes

    updated_course = await courses_controller.courses_repository.update(
        where_=[
            Courses.id == course_id,
        ],
        attributes={"learning_outcomes": learning_outcomes},
        commit=True,
    )

    if not updated_course:
        raise Exception("Failed to update course learning outcomes")

    return Ok(
        data=PutLearningOutcomesCoursesResponse(
            course_id=updated_course.id,
            learning_outcomes=updated_course.learning_outcomes,
        ),
        message="Successfully updated the course learning outcomes.",
    )
