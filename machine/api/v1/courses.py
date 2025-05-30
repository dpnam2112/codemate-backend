import math
from openai import NotFoundError
from sqlalchemy import and_
from machine.models import *
from core.response import Ok
from machine.controllers import *
from utils.data import availableCourses
from machine.schemas.requests import *
from fastapi import APIRouter, Depends, Query
from machine.providers import InternalProvider
from core.utils.auth_utils import verify_token
from machine.schemas.responses.courses import *
from typing import List, Union, Literal, Optional
from machine.schemas.responses.exercise import  *
from fastapi.security import OAuth2PasswordBearer
from machine.schemas.responses.progress_tracking import GetCoursesListResponse
from core.exceptions import BadRequestException, NotFoundException, ForbiddenException
from machine.schemas.responses.learning_path import LearningPathDTO, RecommendedLessonDTO
from fastapi import File, UploadFile
from core.utils.file import update_course_image_s3, generate_presigned_url
import os
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
router = APIRouter(prefix="/courses", tags=["courses"])
# Fixed routes should come first

@router.get("/", response_model=Ok[List[GetCoursesListResponse]])
async def get_courses(
    token: str = Depends(oauth2_scheme),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
    courses_controller: CoursesController = Depends(InternalProvider().get_courses_controller),
):
    """
    Get the list of courses
    """
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    
    # Check if user is professor or student
    professor = await professor_controller.professor_repository.first(where_=[Professor.id == user_id])
    is_professor = professor is not None
    
    if not is_professor:
        student = await student_controller.student_repository.first(where_=[Student.id == user_id])
        if not student:
            raise NotFoundException(message="User not found for the given ID.")
    if is_professor:
        courses = await courses_controller.courses_repository.get_many(
            where_=[Courses.professor_id == user_id],
            order_={"desc": ["start_date"]},
        )
            
    if not courses:
        raise NotFoundException(message="No courses found.")

    course_list = [
        GetCoursesListResponse(
        course_id = course.id,
        course_name = course.name,
        course_courseID = course.courseID,
        course_nSemester = course.nSemester,
        course_class_name = course.class_name,
        course_start_date = course.start_date,
        course_end_date = course.end_date,
        ) for course in courses
    ]
    return Ok(data=course_list, message="Successfully fetched the course list.")

@router.get("/student", response_model=Ok[GetCoursesPaginatedResponse])
async def get_student_courses(
    token: str = Depends(oauth2_scheme),
    page: int = Query(1, description="Page number"),
    page_size: int = Query(10, description="Number of items per page"),
    search_query: Optional[str] = Query(None, description="Search query to filter courses"),
    student_courses_controller: StudentCoursesController = Depends(InternalProvider().get_studentcourses_controller),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
    learning_paths_controller: LearningPathsController = Depends(InternalProvider().get_learningpaths_controller),
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
        Courses.image_url.label("image_url"),
        Courses.nCredit.label("nCredit"),
        Courses.nSemester.label("nSemester"),
        Courses.courseID.label("courseID"),
        Courses.class_name.label("class_name"),
        StudentCourses.last_accessed.label("last_accessed"),
        StudentCourses.percentage_done.label("percentage_complete"),
    ]

    join_conditions = {
        "courses": {"type": "left", "alias": "courses_alias"},
    }

    courses = await student_courses_controller.student_courses_repository._get_many(
        where_=where_conditions,
        fields=select_fields,
        join_=join_conditions,
        order_={"asc": ["last_accessed"]},
        limit=page_size,
        skip=(page - 1) * page_size,
    )

    if not courses:
        empty_response = {
        "content": [],
        "pageSize": page_size,
        "currentPage": page,
        "totalRows": 0,
        "totalPages": 0,
    }
        return Ok(data=empty_response, message="No courses found.")
    
    total_page = math.ceil(len(courses) / page_size)
    content = []
    for course in courses:
        learning_path = await learning_paths_controller.get_learning_path(user_id=user_id, course_id=course.id)
        if learning_path is None: 
            course_response = GetCoursesResponse(
            id=course.id,
            name=course.name,
            start_date=str(course.start_date),
            end_date=str(course.end_date),
            learning_outcomes=course.learning_outcomes or [],
            status=course.status,
            image_url=generate_presigned_url(course.image_url, expiration=604800) if course.image_url else "",
            last_accessed=str(course.last_accessed),
            nCredit=course.nCredit,
            nSemester=course.nSemester,
            courseID=course.courseID,
            class_name=str(course.class_name),
            percentage_complete=str(learning_path.progress) if learning_path else "0",
        )
        else:
            course_response = GetCoursesResponse(
            id=course.id,
            name=course.name,
            start_date=str(course.start_date),
            end_date=str(course.end_date),
            learning_outcomes=course.learning_outcomes or [],
            status=course.status,
            image_url=generate_presigned_url(course.image_url, expiration=604800) if course.image_url else "",
            last_accessed=str(course.last_accessed),
            nCredit=course.nCredit,
            nSemester=course.nSemester,
            courseID=course.courseID,
            class_name=str(course.class_name),
            percentage_complete=str(learning_path.progress) if learning_path else "0",
        )
        content.append(course_response)

            
    courses_response = {
        "content": content,
        "pageSize": page_size,
        "currentPage": page,
        "totalRows": len(courses),
        "totalPages": total_page,
    }
    return Ok(data=courses_response, message="Successfully fetched the courses.")

@router.get("/count/", response_model=Ok[int])
async def count_courses(
    admin_controller: AdminController = Depends(InternalProvider().get_admin_controller),
    token: str = Depends(oauth2_scheme),
    courses_controller: CoursesController = Depends(InternalProvider().get_courses_controller),
):
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    
    check_role = await admin_controller.admin_repository.exists(where_=[Admin.id == user_id])
    if not check_role:
        raise ForbiddenException(message="You are not allowed to access this feature.")

    count = await courses_controller.courses_repository.count(where_=None)

    return Ok(data=count, message="Successfully fetched the count of courses.")

from datetime import date

@router.get("/available", description="Get all available courses of HCMUT")
async def get_available_courses(
    token: str = Depends(oauth2_scheme),
    admin_controller: AdminController = Depends(InternalProvider().get_admin_controller),
):
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    
    check_role = await admin_controller.admin_repository.exists(where_=[Admin.id == user_id])
    # if not check_role:
    #     raise ForbiddenException(message="You are not allowed to access this feature.")
    courses_list = availableCourses
    return Ok(data=courses_list, message="Successfully fetched the available courses.")

@router.post("/add-students", response_model=Ok[AddStudentsToCourseResponse])
async def add_students_to_course(
    request: AddStudentsToCourseRequest,
    token: str = Depends(oauth2_scheme),
    courses_controller: CoursesController = Depends(InternalProvider().get_courses_controller),
    student_courses_controller: StudentCoursesController = Depends(InternalProvider().get_studentcourses_controller),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
    admin_controller: AdminController = Depends(InternalProvider().get_admin_controller),
):
    # Verify admin token
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")

    # Check if user is an admin
    user = await admin_controller.admin_repository.first(where_=[Admin.id == user_id])
    if not user:
        raise NotFoundException(message="Your account is not allowed to add students to courses.")
    
    # Validate request
    if not request.course_id:
        raise BadRequestException(message="Course ID is required.")
    
    if not request.student_ids or len(request.student_ids) == 0:
        raise BadRequestException(message="At least one student ID is required.")
    
    # Check if course exists
    course = await courses_controller.courses_repository.first(where_=[Courses.id == request.course_id])
    if not course:
        raise NotFoundException(message=f"Course with ID {request.course_id} not found.")
    
    # Get students by their MSVVs (student IDs)
    students = await student_controller.student_repository._get_many(
        where_=[Student.mssv.in_(request.student_ids)],
        fields=[Student.id, Student.mssv]
    )
    
    if not students:
        raise NotFoundException(message="No valid students found with the provided IDs.")
    
    # Check which students are already enrolled in the course to avoid duplicates
    existing_enrollments = await student_courses_controller.student_courses_repository._get_many(
        where_=[
            StudentCourses.course_id == request.course_id,
            StudentCourses.student_id.in_([student["id"] for student in students])
        ],
        fields=[StudentCourses.student_id]
    )
    
    # Create a set of already enrolled student IDs for quick lookup
    enrolled_student_ids = {enrollment["student_id"] for enrollment in existing_enrollments}
    
    # Filter out students who are already enrolled
    students_to_enroll = [student for student in students if student["id"] not in enrolled_student_ids]
    
    if not students_to_enroll:
        # Return a success response with 0 added students if all are already enrolled
        return Ok(
            data={
                "course_id": course.id,
                "course_name": course.name,
                "added_students_count": 0,
                "already_enrolled_count": len(request.student_ids),
                "student_courses_list": []
            },
            message="All provided students are already enrolled in this course."
        )
    
    # Prepare attributes for creating new student-course relationships
    student_courses_attributes = [
        {
            "student_id": student["id"],
            "course_id": request.course_id,
        }
        for student in students_to_enroll
    ]
    
    try:
        # Create the student-course relationships
        create_student_courses = await student_courses_controller.student_courses_repository.create_many(
            attributes_list=student_courses_attributes, commit=True
        )
        
        if not create_student_courses:
            raise Exception("Failed to add students to the course - no records returned.")
            
        # Prepare response with safe field access
        student_courses_response = []
        for sc in create_student_courses:
            # Find the matching student MSSV
            student_mssv = None
            for student in students_to_enroll:
                if str(student["id"]) == str(sc.student_id):
                    student_mssv = student["mssv"]
                    break
                    
            # Create a response object with only the fields we know are safe
            student_course_data = StudentCourseInfo(
                student_id=str(sc.student_id),
                student_mssv=student_mssv,
                course_id=str(sc.course_id),
                last_accessed=str(sc.last_accessed) if hasattr(sc, 'last_accessed') else None,
                completed_lessons=sc.completed_lessons if hasattr(sc, 'completed_lessons') else None,
                time_spent=str(sc.time_spent) if hasattr(sc, 'time_spent') else None,
                percentage_done=sc.percentage_done if hasattr(sc, 'percentage_done') else None
            )
            student_courses_response.append(student_course_data)
        
        # Get the count of students who were already enrolled
        already_enrolled_count = len(request.student_ids) - len(students_to_enroll)
        
        response = AddStudentsToCourseResponse(
            course_id=str(course.id),
            course_name=course.name,
            added_students_count=len(create_student_courses),
            already_enrolled_count=already_enrolled_count,
            student_courses_list=student_courses_response
        )
        
        return Ok(
            data=response,
            message=f"Successfully added {len(create_student_courses)} student(s) to the course. {already_enrolled_count} student(s) were already enrolled."
        )
        
    except Exception as e:
        # Simple error handling without checking for specific schema errors
        print(f"Error adding students to course: {str(e)}")
        raise Exception(f"Failed to add students to the course: {str(e)}")
        
@router.get("/admin", description="Get all courses for admin", response_model=Ok[GetAdminCoursesPaginatedResponse])
async def get_courses(
    token: str = Depends(oauth2_scheme),
    search_query: Optional[str] = Query(None, description="Search query to filter courses by name or courseID"),
    page: int = Query(1, description="Page number"),
    page_size: int = Query(10, description="Number of items per page"),
    nCredit: Optional[int] = Query(None, description="Filter courses by number of credits"),
    nSemester: Optional[int] = Query(None, description="Filter courses by semester number"),
    start_date: Optional[date] = Query(None, description="Filter courses by start date (format: YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Filter courses by end date (format: YYYY-MM-DD)"),
    courses_controller: CoursesController = Depends(InternalProvider().get_courses_controller),
    admin_controller: AdminController = Depends(InternalProvider().get_admin_controller),
):
    # Token validation and user authorization
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")

    check_role = await admin_controller.admin_repository.first(where_=[Admin.id == user_id])
    if not check_role:
        raise ForbiddenException(message=f"You are not allowed to access this feature {check_role}")

    # Build the WHERE conditions for filtering
    where_conditions = []

    # Search by name or courseID
    if search_query:
        where_conditions.append(
            (Courses.name.ilike(f"%{search_query}%")) | (Courses.courseID.ilike(f"%{search_query}%"))
        )

    # Filter by nCredit
    if nCredit is not None:
        where_conditions.append(Courses.nCredit == nCredit)

    # Filter by nSemester
    if nSemester is not None:
        where_conditions.append(Courses.nSemester == nSemester)

    # Filter by start_date
    if start_date:
        where_conditions.append(Courses.start_date >= start_date)

    # Filter by end_date
    if end_date:
        where_conditions.append(Courses.end_date <= end_date)

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
        Courses.class_name.label("class_name"),
        Courses.professor_id.label("professor_id"),
    ]

    # Fetch courses based on the filter conditions
    courses = await courses_controller.courses_repository._get_many(
        where_=where_conditions,
        fields=select_fields,
        order_={"desc": ["start_date"]},
        limit=page_size,
        skip=(page - 1) * page_size,
    )

    if not courses:
        empty_response = {
            "content": [],
            "pageSize": page_size,
            "currentPage": page,
            "totalRows": 0,
            "totalPages": 0,
        }
        return Ok(data=empty_response, message="No courses found.")

    # Get total rows for pagination
    total_rows = await courses_controller.courses_repository.count(where_=where_conditions)
    total_pages = math.ceil(total_rows / page_size)

    # Prepare the response
    courses_response = {
        "content": [
            GetAdminCoursesResponse(
                id=course.id,
                name=course.name,
                start_date=str(course.start_date),
                end_date=str(course.end_date),
                status=course.status,
                nCredit=course.nCredit if course.nCredit else 0,
                nSemester=course.nSemester if course.nSemester else 0,
                courseID=course.courseID,
                class_name=course.class_name if course.class_name else "",
                professor_id=course.professor_id if course.professor_id else "",
            )
            for course in courses
        ],
        "pageSize": page_size,
        "currentPage": page,
        "totalRows": total_rows,
        "totalPages": total_pages,
    }
    
    return Ok(data=courses_response, message="Successfully fetched the courses.")

@router.patch("/{course_id}/image", response_model=Ok)
async def update_course_image(
    course_id: str,
    file: UploadFile = File(...),
    token: str = Depends(oauth2_scheme),
    courses_controller: CoursesController = Depends(InternalProvider().get_courses_controller),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
):
    """
    Update course image. If an image already exists, it will be replaced.
    """
    # Verify user token
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    professor = await professor_controller.professor_repository.first(where_=[Professor.id == user_id])
    if not professor:
        raise NotFoundException(message="Only professors have the permission to update course image.")
    # Get the course
    course = await courses_controller.courses_repository.first(where_=[Courses.id == course_id])
    if not course:
        raise NotFoundException(message=f"Course with ID {course_id} not found.")
    
    # Check if user is the professor of this course
    if course.professor_id != professor.id:
        raise ForbiddenException(message="You don't have permission to update this course.")
    
    # Check file type
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif']
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in allowed_extensions:
        raise BadRequestException(message="Invalid file type. Only JPG, JPEG, PNG, and GIF files are allowed.")
    
    # Read file content
    file_content = await file.read()
    
    # Extract the existing image key from the course (if it exists)
    existing_image_key = course.image_url
    
    # Handle the S3 operations
    s3_key, presigned_url = await update_course_image_s3(
        existing_image_key, 
        file_content,
        f"course_{course_id}{file_extension}"
    )
    
    # Update the course with the new image URL
    await courses_controller.courses_repository.update(
        where_=[Courses.id == course_id],
        attributes={"image_url": s3_key},
        commit = True
    )
    
    return Ok(
        message="Course image updated successfully.", 
        data={"image_url": presigned_url}
    )

@router.get("/{courseId}", response_model=Ok[GetCourseDetailResponse])
async def get_course_for_student(
    courseId: str,
    token: str = Depends(oauth2_scheme),
    student_courses_controller: StudentCoursesController = Depends(InternalProvider().get_studentcourses_controller),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
    learning_paths_controller: LearningPathsController = Depends(InternalProvider().get_learningpaths_controller),
):
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")

    student = await student_controller.student_repository.first(where_=[Student.id == user_id])
    if not student:
        raise ForbiddenException(message=f"Your account is not allowed to access this feature. {student}")

    select_fields = [
        Courses.name.label("name"),
        Courses.id.label("id"),
        Courses.start_date.label("start_date"),
        Courses.end_date.label("end_date"),
        Courses.learning_outcomes.label("learning_outcomes"),
        Courses.status.label("status"),
        Courses.image_url.label("image_url"),
        Courses.nCredit.label("nCredit"),
        Courses.nSemester.label("nSemester"),
        Courses.courseID.label("courseID"),
        Courses.class_name.label("class_name"),
        Courses.courseID.label("courseID"),
        StudentCourses.last_accessed.label("last_accessed"),
        StudentCourses.completed_lessons.label("completed_lessons"),
        StudentCourses.time_spent.label("time_spent"),
        StudentCourses.percentage_done.label("percentage_done"),
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
    try:
        learning_path = await learning_paths_controller.get_learning_path(user_id=user_id, course_id=courseId)
    except NotFoundException:
        learning_path = None
    if not course:
        course_response = GetCourseDetailResponse(
            course_id=courseId,
            course_name="",
            course_start_date="",
            course_end_date="",
            course_learning_outcomes=[],
            course_status="",
            course_image="",
            course_nCredit=0,
            course_nSemester=0,
            course_courseID="",
            course_classname="",
            course_percentage_complete="",
            course_last_accessed="",
            completed_lessons=0,
            time_spent="",
            percentage_done=0,
        )
        return Ok(data=course_response, message="You are not enrolled in this course.")
    image_url = ""
    if get_course.image_url:
        image_url = generate_presigned_url(get_course.image_url, expiration=604800)
    course_response = GetCourseDetailResponse(
        course_id=str(courseId),
        course_name=get_course.name,
        course_start_date=str(get_course.start_date) if get_course.start_date else "",
        course_end_date=str(get_course.end_date) if get_course.end_date else "",
        course_learning_outcomes=get_course.learning_outcomes or [],
        course_status=get_course.status,
        course_image=image_url if get_course.image_url else "",
        course_nCredit=get_course.nCredit,
        course_nSemester=get_course.nSemester,
        course_courseID=get_course.courseID,
        course_classname=get_course.class_name,
        course_percentage_complete=str(learning_path.progress) if learning_path else "0",
        course_last_accessed=str(get_course.last_accessed) if get_course.last_accessed else "",
        completed_lessons=get_course.completed_lessons or 0,
        time_spent=str(get_course.time_spent) if get_course.time_spent else "",
        percentage_done=str(learning_path.progress) if learning_path else "0",
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
        Student.mssv.label("ms"),
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
            student_mssv=student.ms,
        )
        for student in students
    ]

    return Ok(data=students_response, message="Successfully fetched the students.")

@router.get("/{courseId}/lessons", response_model=Ok[List[GetLessonsResponse]])
async def get_lessons_for_course(
    courseId: str,
    token: str = Depends(oauth2_scheme),
    lessons_controller: LessonsController = Depends(InternalProvider().get_lessons_controller),
    documents_controller: DocumentsController = Depends(InternalProvider().get_documents_controller),
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
            nDocuments= await documents_controller.documents_repository.count(where_=[Documents.lesson_id == lesson.id]),
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
    request: List[CreateCourseRequest],
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
    
    if not request or len(request) == 0:
        raise BadRequestException(message="At least one course is required.")

    if len(request) == 1:
        if not request[0].nSemester or not request[0].class_name:
            raise BadRequestException(message="Semester and class name are required.")
        checkIfCourseExists = await courses_controller.courses_repository.first(
            where_=[Courses.courseID == request[0].courseID, Courses.nSemester == request[0].nSemester, Courses.class_name == request[0].class_name]
        )
        if checkIfCourseExists:
            raise BadRequestException(message="Course already exists.")
        saveProfessorId = await professors_controller.professor_repository.first(
            Professor.mscb == request[0].professorID
        )
        saveProfessorId = saveProfessorId.id
        course_attributes = {
            "name": request[0].name,
            "professor_id": saveProfessorId,
            "nCredit": request[0].creditNumber,
            "nSemester": request[0].nSemester,
            "createdByAdminID": user_id,
            "courseID": request[0].courseID,
            "start_date": request[0].startDate,
            "end_date": request[0].endDate,
            "class_name": request[0].class_name,
        }

        createCourse = await courses_controller.courses_repository.create(attributes=course_attributes, commit=True)
        if not createCourse:
            raise Exception("Failed to create course")

        getStudentIDs = await student_controller.student_repository._get_many(
    where_=[Student.mssv.in_(request[0].studentIDs)],
    fields=[Student.id]
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
                "student_id": create_student_course.student_id,
                "course_id": createCourse.id,
                "last_accessed": str(create_student_course.last_accessed),
                "completed_lessons": create_student_course.completed_lessons,
                "time_spent": str(create_student_course.time_spent),
                "percentage_done": create_student_course.percentage_done,
            }
            for create_student_course in create_student_courses
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
            "class_name": createCourse.class_name,
        }
        return Ok(data=course_response, message="Successfully created the course.")
    else:
        professor_ids = [course.professorID for course in request]
        professors = await professors_controller.professor_repository._get_many(
            where_=[Professor.mscb.in_(professor_ids)], fields=[Professor.id, Professor.mscb]
        )

        professor_id_map = {prof["mscb"]: prof["id"] for prof in professors}

        courses_attributes = []
        for course in request:
            if not course.nSemester or not course.class_name:
                raise BadRequestException(message="Semester and class name are required.")
            checkIfCourseExists = await courses_controller.courses_repository.first(
                where_=[Courses.courseID == course.courseID, Courses.nSemester == course.nSemester, Courses.class_name == course.class_name]
            )
            if checkIfCourseExists:
                raise BadRequestException(message="Course already exists.")
            if not course.name:
                raise BadRequestException(message="Course name is required.")

            professor_id = professor_id_map.get(course.professorID)
            if not professor_id:
                raise NotFoundException(message=f"Professor with mscb {course.professorID} not found")

            course_attr = {
                "name": course.name,
                "professor_id": professor_id,
                "nCredit": course.creditNumber,
                "nSemester": course.nSemester,
                "createdByAdminID": user_id,
                "status": "new",
                "courseID": course.courseID,
                "start_date": course.startDate,
                "end_date": course.endDate,
                "class_name": course.class_name,
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
        for created_course, request_course in zip(create_courses, request):

            student_ids = request_course.studentIDs
            students = await student_controller.student_repository._get_many(
                where_=[Student.mssv.in_(student_ids)], fields=[Student.id, Student.mssv]
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
                    "percentage_done": sc.percentage_done,
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
                "class_name": created_course.class_name,
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

@router.get(
    "/{course_id}/students/{student_id}/learning-path/recommended-lessons",
)
async def get_recommended_lessons(
    course_id: UUID,
    student_id: UUID,
    token: str = Depends(oauth2_scheme),
    expand: Optional[Literal["modules"]] = Query(None, description="Expand related data, e.g., 'modules'."),
    lp_controller: LearningPathsController = Depends(InternalProvider().get_learningpaths_controller),
):
    payload = verify_token(token)
    professor_id = payload.get("sub")
    if not professor_id:
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

@router.get("/{course_id}/exercises", response_model=Ok[List[GetExercise]])
async def get_course_exercises(
    course_id: UUID,
    token: str = Depends(oauth2_scheme),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
    exercises_controller: ExercisesController = Depends(InternalProvider().get_exercises_controller),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
    courses_controller: CoursesController = Depends(InternalProvider().get_courses_controller)
):
    # Verify access
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    
    # Check if user is professor or student
    professor = await professor_controller.professor_repository.first(where_=[Professor.id == user_id])
    is_professor = professor is not None
    
    if not is_professor:
        student = await student_controller.student_repository.first(where_=[Student.id == user_id])
        if not student:
            raise NotFoundException(message="User not found for the given ID.")
    
    # Base query conditions
    conditions = [Exercises.course_id == course_id]
    
    # Add time filter for students
    current_time = datetime.now()
    if not is_professor:
        conditions.append(Exercises.time_open <= current_time)
    course = await courses_controller.courses_repository.first(where_=[Courses.id == course_id])
    if not course:
        raise NotFoundException(message="Course not found for the given ID.")
    # Get exercises with ordering
    exercises = await exercises_controller.exercises_repository.get_many(
        where_=conditions,
        order_={"desc": ["time_open"]},  
    )
    return Ok[List[GetExercise]](data=[
        GetExercise(
            id=exercise.id,
            name=exercise.name,
            description=exercise.description,
            type=exercise.type,
            time_open=exercise.time_open.strftime("%H:%M %d/%m/%Y"),
            time_close=exercise.time_close.strftime("%H:%M %d/%m/%Y"),
            time_limit=exercise.time_limit,
            attempts_allowed=exercise.attempts_allowed,
            grading_method=exercise.grading_method,
        ) for exercise in exercises
    ])
    
@router.patch("/admin/{course_id}")
async def update_course(
    course_id: UUID,
    request: UpdateCourseRequest,
    token: str = Depends(oauth2_scheme),
    courses_controller: CoursesController = Depends(InternalProvider().get_courses_controller),
    admin_controller: AdminController = Depends(InternalProvider().get_admin_controller),
):
    # Verify token and extract user ID
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    
    # Check if user has the correct admin role
    check_role = await admin_controller.admin_repository.first(where_=[Admin.id == user_id])
    if not check_role:
        raise ForbiddenException(message="You are not allowed to access this feature.")

    # Prepare the course attributes to update, only including provided fields
    course_attributes = {}

    if request.name is not None:
        course_attributes["name"] = request.name
    if request.n_credit is not None:
        course_attributes["nCredit"] = request.n_credit
    if request.n_semester is not None:
        course_attributes["nSemester"] = request.n_semester
    if request.courseID is not None:
        course_attributes["courseID"] = request.courseID
    if request.start_date is not None:
        course_attributes["start_date"] = request.start_date
    if request.end_date is not None:
        course_attributes["end_date"] = request.end_date
    if request.class_name is not None:
        course_attributes["class_name"] = request.class_name
    if request.professor_id is not None:
        course_attributes["professor_id"] = request.professor_id
    if request.status is not None:
        course_attributes["status"] = request.status

    # Update the course with the attributes that have been provided
    update_course = await courses_controller.courses_repository.update(
        where_=[Courses.id == course_id],
        attributes=course_attributes,
        commit=True
    )

    if not update_course:
        raise BadRequestException(message="Failed to update course.")
    
    return Ok(data=None, message="Successfully updated the course.")

@router.delete("/admin/{course_id}")
async def delete_course(
    course_id: UUID,
    token: str = Depends(oauth2_scheme),
    courses_controller: CoursesController = Depends(InternalProvider().get_courses_controller),
    student_courses_controller: StudentCoursesController = Depends(InternalProvider().get_studentcourses_controller),
    admin_controller: AdminController = Depends(InternalProvider().get_admin_controller),
):
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    
    check_role = await admin_controller.admin_repository.first(where_=[Admin.id == user_id])
    if not check_role:
        raise ForbiddenException(message="You are not allowed to access this feature.")

    # Delete the course and its associated data
    await courses_controller.courses_repository.delete(where_=[Courses.id == course_id])
    await student_courses_controller.student_courses_repository.delete(where_=[StudentCourses.course_id == course_id])
    await courses_controller.courses_repository.session.commit()
    await student_courses_controller.student_courses_repository.session.commit()

    return Ok(data=None, message="Successfully deleted the course."
)

@router.get("/issues/{course_id}")
async def get_course_issues(
    course_id: UUID,
    token: str = Depends(oauth2_scheme),
    student_courses_controller: StudentCoursesController = Depends(InternalProvider().get_studentcourses_controller),
):
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    
    # Get the course
    course = await student_courses_controller.student_courses_repository.first(where_=[StudentCourses.course_id == course_id])
    if not course:
        raise NotFoundException(message="Student does not enroll in this course.")
    # Get the course issues
    
    response = {
        "issues_summary" : course.issues_summary
    }
    
    return Ok(data=response, message="Successfully fetched the course issues.")
