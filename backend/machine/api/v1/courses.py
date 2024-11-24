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


@router.post("/", response_model=Ok[GetCoursesPaginatedResponse])
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
        ProfessorUser.avatar_url.label("professor_avatar"),
        StudentUser.id.label("student_id"),
        StudentUser.name.label("student_name"),
        StudentUser.email.label("student_email"),
        StudentUser.avatar_url.label("student_avatar"),
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
        #limit=request.page_size,
        fields=select_fields,
        where_=where_conditions,
        join_=join_conditions,
        group_by_=group_by_fields,
        order_=order_conditions,
    )

    #total_rows = await courses_controller.courses_repository.count(where_=where_conditions)
    total_rows = len(paginated_courses)
    total_pages = total_rows // request.page_size
    if total_pages == 0:
        total_pages = 1

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
                percentage_complete=f"{(course.completed_lessons/course.total_lessons*100) if course.total_lessons > 0 else 0:.0f}",
                last_accessed=course.last_accessed.isoformat() if course.last_accessed else None,
                professor=ProfessorInformation(
                    professor_id=course.professor_id,
                    professor_name=course.professor_name,
                    professor_email=course.professor_email,
                    professor_avatar=str(course.professor_avatar) if course.professor_avatar else "",
                ),
                student_list=[
                    StudentList(
                        student_id=request.student_id,
                        student_name=course.student_name or "",
                        student_email=course.student_email or "",
                        student_avatar=str(course.student_avatar) if course.student_avatar else ""
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
    lessons_controller: LessonsController = Depends(InternalProvider().get_lessons_controller),
    exercises_controller: ExercisesController = Depends(InternalProvider().get_exercises_controller),
    student_lessons_controller: StudentLessonsController = Depends(InternalProvider().get_studentlessons_controller),
    student_exercises_controller: StudentExercisesController = Depends(InternalProvider().get_studentexercises_controller),
    document_controller: DocumentsController = Depends(InternalProvider().get_documents_controller),
):
    # Validate input
    if not courseId or not studentId:
        raise BadRequestException(message="Student ID and Course ID are required.")

    # Check if the student is enrolled in the course
    student_course = await student_courses_controller.student_courses_repository.first(
        where_=[and_(StudentCourses.student_id == studentId, StudentCourses.course_id == courseId)]
    )
    if not student_course:
        raise BadRequestException(message="Student is not enrolled in this course.")

    # Fetch lessons for the course
    lessons = await lessons_controller.lessons_repository.get_many(
        where_=[Lessons.course_id == courseId],
        order_={"asc": ["order"]},
    )

    # Fetch student lessons for the student in this course
    lesson_ids = [lesson.id for lesson in lessons]
    student_lessons = await student_lessons_controller.student_lessons_repository.get_many(
        where_=[and_(
            StudentLessons.student_id == studentId,
            StudentLessons.lesson_id.in_(lesson_ids),
            StudentLessons.lesson_type == LessonType.original
        )]
    )
    student_lessons_by_lesson = {sl.lesson_id: sl for sl in student_lessons}

    # Fetch exercises for the lessons
    exercises = await exercises_controller.exercises_repository.get_many(
        where_=[Exercises.lesson_id.in_(lesson_ids)],
    )
    exercises_by_lesson = {}
    for exercise in exercises:
        exercises_by_lesson.setdefault(exercise.lesson_id, []).append(exercise)

    # Fetch student exercises for the student
    exercise_ids = [exercise.id for exercise in exercises]
    student_exercises = await student_exercises_controller.student_exercises_repository.get_many(
        where_=[StudentExercises.student_id == studentId, StudentExercises.exercise_id.in_(exercise_ids)],
    )
    student_exercises_by_exercise = {se.exercise_id: se for se in student_exercises}

    # Fetch documents for the lessons
    lesson_documents = await document_controller.documents_repository.get_many(
        where_=[Documents.lesson_id.in_(lesson_ids)],
    )
    documents_by_lesson = {}
    for document in lesson_documents:
        documents_by_lesson.setdefault(document.lesson_id, []).append(document)

    # Transform lessons into the response model
    lessons_response: List[GetLessonsResponse] = []
    for lesson in lessons:
        student_lesson = student_lessons_by_lesson.get(lesson.id)
        lesson_exercises = exercises_by_lesson.get(lesson.id, [])
        lesson_documents = documents_by_lesson.get(lesson.id, [])

        lessons_response.append(
            GetLessonsResponse(
                id=lesson.id,
                title=lesson.title,
                description=lesson.description or "",
                lesson_type=student_lesson.lesson_type if student_lesson else LessonType.original,
                bookmark=student_lesson.bookmark if student_lesson else False,
                order=lesson.order,
                status=student_lesson.status if student_lesson else "New",
                exercises=[
                    GetExercisesResponse(
                        id=exercise.id,
                        name=exercise.name,
                        description=exercise.description or "",
                        status=student_exercises_by_exercise[exercise.id].status
                        if exercise.id in student_exercises_by_exercise else "New",
                        type=exercise.type,
                    )
                    for exercise in lesson_exercises
                ],
                documents=[
                    GetDocumentsResponse(
                        id=document.id,
                        name=document.name,
                        type=document.type,
                        url=document.document_url,
                    )
                    for document in lesson_documents
                ]
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


@router.put("/{courseId}/students/{studentId}/lessons/{lessonId}/bookmark", response_model=Ok[bool])
async def bookmark_lesson(
    courseId: UUID,
    studentId: UUID,
    lessonId: UUID,
    student_lessons_controller: StudentLessonsController = Depends(InternalProvider().get_studentlessons_controller),
):
    if not lessonId or not courseId or not studentId:
        raise BadRequestException(message="Student ID, Course ID, and Lesson ID are required.")

    # Find the existing lesson
    lesson = await student_lessons_controller.student_lessons_repository.first(
        where_=[
            StudentLessons.lesson_id == lessonId,
            StudentLessons.student_id == studentId,
            StudentLessons.course_id == courseId,
        ]
    )

    if not lesson:
        raise BadRequestException(message="Lesson not found.")

    # Toggle the bookmark status
    new_bookmark_status = not lesson.bookmark

    # Update with commit
    updated_lesson = await student_lessons_controller.student_lessons_repository.update(
        where_=[
            StudentLessons.lesson_id == lessonId,
            StudentLessons.student_id == studentId,
            StudentLessons.course_id == courseId,
        ],
        attributes={"bookmark": new_bookmark_status},
        commit=True,  # Important: commit the transaction
    )

    if not updated_lesson:
        raise Exception("Failed to update lesson bookmark status")

    # Verify the update was successful
    if updated_lesson.bookmark != new_bookmark_status:
        raise Exception("Bookmark status was not updated correctly")

    return Ok(
        data=new_bookmark_status,
        message="Successfully {} the lesson.".format(
            "bookmarked" if new_bookmark_status else "removed the bookmark from"
        ),
    )

@router.get("/{courseId}/students/{studentId}/lessons_recommendation/", response_model=Ok[List[GetLessonsRecommendationResponse]])
async def get_lessons_recommendation(
    courseId: UUID,
    studentId: UUID,
    student_lessons_controller: StudentLessonsController = Depends(InternalProvider().get_studentlessons_controller),
):
    if not courseId or not studentId:
        raise BadRequestException(message="Both Student ID and Course ID are required.")

    where_conditions = [
        StudentLessons.student_id == studentId,
        StudentLessons.course_id == courseId,
        StudentLessons.lesson_type == LessonType.recommended,
    ]

    join_conditions = {
        "lessons": {"type": "left", "alias": "lessons"},
    }

    recommended_lessons_list = await student_lessons_controller.student_lessons_repository._get_many(
        where_=where_conditions,
        join_=join_conditions,
        fields=[
            StudentLessons.course_id.label("course_id"),
            StudentLessons.lesson_id.label("lesson_id"),
            Lessons.title.label("title"),
            Lessons.description.label("description"),
            Lessons.order.label("order"),
            StudentLessons.lesson_type.label("lesson_type"),
            StudentLessons.bookmark.label("bookmark"),
            StudentLessons.status.label("status"),
        ],
    )

    recommended_lessons: List[GetLessonsRecommendationResponse] = []
    for lesson in recommended_lessons_list:
        recommended_lessons.append(
            GetLessonsRecommendationResponse(
                course_id=lesson.course_id, 
                lesson_id=lesson.lesson_id,
                title=lesson.title,
                description=lesson.description or "",
                lesson_type=lesson.lesson_type,
                bookmark=lesson.bookmark,
                order=lesson.order,
                status=lesson.status,
            )
        )

    return Ok(data=recommended_lessons, message="Successfully fetched the recommended lessons.")
