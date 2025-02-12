from typing import List, Literal
from machine.models import *
from core.response import Ok
from machine.controllers import *
from sqlalchemy.orm import aliased
from sqlalchemy import literal_column
from fastapi import APIRouter, Depends, Query, status
from machine.schemas.requests import *
from core.repository.enum import UserRole
from sqlalchemy.sql import func, and_, or_
from machine.providers import InternalProvider
from machine.schemas.responses.courses import *
from core.exceptions import BadRequestException, NotFoundException
from machine.schemas.responses.learning_path import LearningPathDTO, RecommendedLessonDTO

router = APIRouter(prefix="/courses", tags=["courses"])


@router.post("/", response_model=Ok[GetCoursesPaginatedResponse])
async def get_courses(
    request: GetCoursesRequest,
    courses_controller: CoursesController = Depends(InternalProvider().get_courses_controller),
    users_controller: UserController = Depends(InternalProvider().get_user_controller),
):
    if not request.student_id:
        raise BadRequestException(message="Student ID is required.")
    where_conditions = [StudentCourses.student_id == request.student_id]


    select_fields = [
        Courses.id.label("id"),
    ]
    join_conditions = {"student_courses": {"type": "left", "alias": "student_courses"}}

    student_courses = await courses_controller.courses_repository._get_many(
        where_=where_conditions,
        fields=select_fields,
        join_=join_conditions,
    )
    course_ids = [sc.id for sc in student_courses]

    if not course_ids:
        return NotFoundException(message="No courses found for the student.")

    ProfessorUser = aliased(User)

    where_conditions = [StudentCourses.course_id.in_(course_ids)]
    
    if request.search_query:
        search_condition = or_(
            Courses.name.ilike(f"%{request.search_query}%"),
            ProfessorUser.name.ilike(f"%{request.search_query}%"),
        )
        where_conditions.append(search_condition)
    
    join_conditions = {
        "student_courses": {"type": "left", "alias": "student_courses"},
        "courses": {"type": "left", "alias": "courses"},
        "professor": {"type": "left", "table": ProfessorUser, "alias": "professor_alias"},
    }
    select_fields = [
        Courses.id.label("id"),
        Courses.name.label("name"),
        Courses.start_date.label("start_date"),
        Courses.end_date.label("end_date"),
        Courses.learning_outcomes.label("learning_outcomes"),
        Courses.status.label("status"),
        Courses.image_url.label("image_url"),
        Courses.professor_id.label("professor_id"),
        func.count(Lessons.id).label("total_lessons"),
        StudentCourses.completed_lessons.label("completed_lessons"),
        StudentCourses.time_spent.label("time_spent"),
        StudentCourses.assignments_done.label("assignments_done"),
        StudentCourses.last_accessed.label("last_accessed"),
        User.id.label("student_id"),
        User.name.label("student_name"),
        User.email.label("student_email"),
        User.avatar_url.label("student_avatar"),
        ProfessorUser.name.label("professor_name"),
        ProfessorUser.email.label("professor_email"),
        ProfessorUser.avatar_url.label("professor_avatar"),
    ]

    group_by_fields = [
        Courses.id,
        Courses.name,
        Courses.start_date,
        Courses.end_date,
        Courses.learning_outcomes,
        Courses.status,
        Courses.image_url,
        Courses.professor_id,
        StudentCourses.completed_lessons,
        StudentCourses.time_spent,
        StudentCourses.assignments_done,
        StudentCourses.last_accessed,
        User.id,
        User.name,
        User.email,
        User.avatar_url,
        ProfessorUser.name,
        ProfessorUser.email,
        ProfessorUser.avatar_url,
    ]

    order_conditions = {"asc": ["name"]}

    courses = await users_controller.user_repository._get_many(
        where_=where_conditions,
        fields=select_fields,
        join_=join_conditions,
        order_=order_conditions,
        group_by_=group_by_fields,
    )

    course_map = {}

    for course in courses:
        course_id = course.id

        if course_id not in course_map:
            course_map[course_id] = {
                "id": course.id,
                "name": course.name,
                "start_date": str(course.start_date),
                "end_date": str(course.end_date),
                "student_list": [],
                "learning_outcomes": course.learning_outcomes,
                "professor": ProfessorInformation(
                    professor_id=course.professor_id,
                    professor_name=course.professor_name,
                    professor_email=course.professor_email,
                    professor_avatar=str(course.professor_avatar),
                ),
                "status": course.status,
                "image": str(course.image_url),
                "percentage_complete": f"{(course.completed_lessons / course.total_lessons * 100) if course.total_lessons > 0 else 0:.0f}",
                "last_accessed": str(course.last_accessed),
            }

        course_map[course_id]["student_list"].append(
            StudentList(
                student_id=course.student_id,
                student_name=course.student_name,
                student_email=course.student_email,
                student_avatar=str(course.student_avatar),
            )
        )
    response_content = [GetCoursesResponse(**course_data) for course_data in course_map.values()]
    total_rows = len(response_content)
    total_pages = total_rows // request.page_size
    if total_pages == 0:
        total_pages = 1
    
    response_content = response_content[request.offset : request.offset + request.page_size]
    response = Ok(
        data=GetCoursesPaginatedResponse(
            content=response_content,
            currentPage=(request.offset // request.page_size) + 1,
            pageSize=request.page_size,
            totalRows=total_rows,
            totalPages=total_pages,
        ),
        message="Successfully fetched the courses.",
    )

    return response


@router.get("/{courseId}/students/{studentId}/", response_model=Ok[GetCourseDetailResponse])
async def get_course_for_student(
    courseId: str,
    studentId: str,
    courses_controller: CoursesController = Depends(InternalProvider().get_courses_controller),
    student_courses_controller: StudentCoursesController = Depends(InternalProvider().get_studentcourses_controller),
    lessons_controller: LessonsController = Depends(InternalProvider().get_lessons_controller),
    exercises_controller: ExercisesController = Depends(InternalProvider().get_exercises_controller),
    student_lessons_controller: StudentLessonsController = Depends(InternalProvider().get_studentlessons_controller),
    student_exercises_controller: StudentExercisesController = Depends(
        InternalProvider().get_studentexercises_controller
    ),
    document_controller: DocumentsController = Depends(InternalProvider().get_documents_controller),
):
    if not courseId or not studentId:
        raise BadRequestException(message="Student ID and Course ID are required.")

    student_course = await student_courses_controller.student_courses_repository.first(
        where_=[and_(StudentCourses.student_id == studentId, StudentCourses.course_id == courseId)]
    )
    if not student_course:
        raise BadRequestException(message="Student is not enrolled in this course.")

    where_conditions = [StudentCourses.course_id == courseId, StudentCourses.student_id == studentId]
    join_conditions = {
        "student_courses": {"type": "left", "alias": "student_courses"},
        "professor": {"type": "left", "alias": "professor_alias"},
    }
    select_fields = [
        Courses.id.label("course_id"),
        Courses.name.label("course_name"),
        Courses.start_date.label("course_start_date"),
        Courses.end_date.label("course_end_date"),
        Courses.learning_outcomes.label("course_learning_outcomes"),
        Courses.professor_id.label("course_professor_id"),
        Courses.status.label("course_status"),
        Courses.image_url.label("course_image_url"),
        User.name.label("user_professor_name"),
        User.email.label("user_professor_email"),
        User.avatar_url.label("user_professor_avatar"),
    ]

    get_orther_course_data = await courses_controller.courses_repository._get_many(
        where_=where_conditions,
        fields=select_fields,
        join_=join_conditions,
    )

    get_orther_course_data = get_orther_course_data[0]

    lessons = await lessons_controller.lessons_repository.get_many(
        where_=[Lessons.course_id == courseId],
        order_={"asc": ["order"]},
    )

    lesson_ids = [lesson.id for lesson in lessons]
    student_lessons = await student_lessons_controller.student_lessons_repository.get_many(
        where_=[
            and_(
                StudentLessons.student_id == studentId,
                StudentLessons.lesson_id.in_(lesson_ids),
            )
        ]
    )
    student_lessons_by_lesson = {sl.lesson_id: sl for sl in student_lessons}

    exercises = await exercises_controller.exercises_repository.get_many(
        where_=[Exercises.lesson_id.in_(lesson_ids)],
    )
    exercises_by_lesson = {}
    for exercise in exercises:
        exercises_by_lesson.setdefault(exercise.lesson_id, []).append(exercise)

    exercise_ids = [exercise.id for exercise in exercises]
    student_exercises = await student_exercises_controller.student_exercises_repository.get_many(
        where_=[StudentExercises.student_id == studentId, StudentExercises.exercise_id.in_(exercise_ids)],
    )
    student_exercises_by_exercise = {se.exercise_id: se for se in student_exercises}

    lesson_documents = await document_controller.documents_repository.get_many(
        where_=[Documents.lesson_id.in_(lesson_ids)],
    )
    documents_by_lesson = {}
    for document in lesson_documents:
        documents_by_lesson.setdefault(document.lesson_id, []).append(document)

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
                bookmark=student_lesson.bookmark if student_lesson else False,
                order=lesson.order,
                exercises=[
                    GetExercisesResponse(
                        id=exercise.id,
                        name=exercise.name,
                        description=exercise.description or "",
                        status=(
                            student_exercises_by_exercise[exercise.id].status
                            if exercise.id in student_exercises_by_exercise
                            else "New"
                        ),
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
                ],
            )
        )
    response = GetCourseDetailResponse(
        course_id=get_orther_course_data.course_id,
        course_name=get_orther_course_data.course_name,
        course_start_date=str(get_orther_course_data.course_start_date),
        course_end_date=str(get_orther_course_data.course_end_date),
        course_learning_outcomes=get_orther_course_data.course_learning_outcomes,
        course_professor=ProfessorInformation(
            professor_id=get_orther_course_data.course_professor_id,
            professor_name=get_orther_course_data.user_professor_name,
            professor_email=get_orther_course_data.user_professor_email,
            professor_avatar=str(get_orther_course_data.user_professor_avatar),
        ),
        course_status=get_orther_course_data.course_status,
        course_image=str(get_orther_course_data.course_image_url),
        course_percentage_complete=f"{(student_course.completed_lessons / len(lessons) * 100):.0f}",
        student_id=student_course.student_id,
        course_last_accessed=str(student_course.last_accessed),
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

    lesson = await student_lessons_controller.student_lessons_repository.first(
        where_=[
            StudentLessons.lesson_id == lessonId,
            StudentLessons.student_id == studentId,
            StudentLessons.course_id == courseId,
        ]
    )

    if not lesson:
        raise BadRequestException(message="Lesson not found.")

    new_bookmark_status = not lesson.bookmark

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

    if updated_lesson.bookmark != new_bookmark_status:
        raise Exception("Bookmark status was not updated correctly")

    return Ok(
        data=new_bookmark_status,
        message="Successfully {} the lesson.".format(
            "bookmarked" if new_bookmark_status else "removed the bookmark from"
        ),
    )

@router.get(
    "/{course_id}/students/{studentId}/learning-path",
    response_model=Ok[LearningPathDTO]
)
async def get_personalized_lp(
    course_id: UUID,
    student_id: UUID,
    lp_controller: LearningPathsController = Depends(InternalProvider().get_learningpaths_controller)
):
    lp = await lp_controller.get_learning_path(
        course_id=course_id, user_id=student_id
    )

    return Ok(data=LearningPathDTO.model_validate(lp))
@router.get(
    "/{course_id}/students/{student_id}/learning-path/recommended-lessons",
    response_model=Ok[List[RecommendedLessonDTO]]
)
async def get_recommended_lessons(
    course_id: UUID,
    student_id: UUID,
    expand: Optional[Literal["modules"]] = Query(None, description="Expand related data, e.g., 'modules'."),
    lp_controller: LearningPathsController = Depends(InternalProvider().get_learningpaths_controller)
):
    recommended_lessons = await lp_controller.get_recommended_lessons(
        user_id=student_id, 
        course_id=course_id, 
        expand=expand
    )

    return Ok(data=recommended_lessons)


@router.delete(
    "/{course_id}/students/{student_id}/learning-path"
)
async def delete_learning_path(
    course_id: UUID,
    student_id: UUID,
    lp_controller: LearningPathsController = Depends(InternalProvider().get_learningpaths_controller)
):
    await lp_controller.delete_learning_path(user_id=student_id, course_id=course_id)
    return None
