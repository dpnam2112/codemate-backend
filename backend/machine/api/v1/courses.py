from typing import List, Union
from machine.models import *
from core.response import Ok
from machine.controllers import *
from sqlalchemy.orm import aliased
from fastapi import APIRouter, Depends
from machine.schemas.requests import *
from data.constant import expectedHeaders
from sqlalchemy.sql import func, and_, or_
from machine.providers import InternalProvider
from core.utils.auth_utils import verify_token
from machine.schemas.responses.courses import *
from fastapi.security import OAuth2PasswordBearer
from core.exceptions import BadRequestException, NotFoundException

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
router = APIRouter(prefix="/courses", tags=["courses"])


# @router.post("/", response_model=Ok[GetCoursesPaginatedResponse])
# async def get_courses(
#     request: GetCoursesRequest,
#     courses_controller: CoursesController = Depends(InternalProvider().get_courses_controller),
#     student_controller: StudentController = Depends(InternalProvider().get_student_controller),
# ):
#     if not request.student_id:
#         raise BadRequestException(message="Student ID is required.")
#     where_conditions = [StudentCourses.student_id == request.student_id]

#     select_fields = [
#         Courses.id.label("id"),
#     ]
#     join_conditions = {"student_courses": {"type": "left", "alias": "student_courses"}}

#     student_courses = await courses_controller.courses_repository._get_many(
#         where_=where_conditions,
#         fields=select_fields,
#         join_=join_conditions,
#     )
#     course_ids = [sc.id for sc in student_courses]

#     if not course_ids:
#         return NotFoundException(message="No courses found for the student.")

#     ProfessorAlias = aliased(Professor)

#     where_conditions = [StudentCourses.course_id.in_(course_ids)]

#     if request.search_query:
#         search_condition = or_(
#             Courses.name.ilike(f"%{request.search_query}%"),
#             ProfessorAlias.name.ilike(f"%{request.search_query}%"),
#         )
#         where_conditions.append(search_condition)

#     join_conditions = {
#         "student_courses": {"type": "left", "alias": "student_courses"},
#         "courses": {"type": "left", "alias": "courses"},
#         "professor": {"type": "left", "table": ProfessorAlias, "alias": "professor_alias"},
#     }
#     select_fields = [
#         Courses.id.label("id"),
#         Courses.name.label("name"),
#         Courses.start_date.label("start_date"),
#         Courses.end_date.label("end_date"),
#         Courses.learning_outcomes.label("learning_outcomes"),
#         Courses.status.label("status"),
#         Courses.image_url.label("image_url"),
#         Courses.professor_id.label("professor_id"),
#         func.count(Lessons.id).label("total_lessons"),
#         StudentCourses.completed_lessons.label("completed_lessons"),
#         StudentCourses.time_spent.label("time_spent"),
#         StudentCourses.assignments_done.label("assignments_done"),
#         StudentCourses.last_accessed.label("last_accessed"),
#         Student.id.label("student_id"),
#         Student.name.label("student_name"),
#         Student.email.label("student_email"),
#         Student.avatar_url.label("student_avatar"),
#         ProfessorAlias.name.label("professor_name"),
#         ProfessorAlias.email.label("professor_email"),
#         ProfessorAlias.avatar_url.label("professor_avatar"),
#     ]

#     group_by_fields = [
#         Courses.id,
#         Courses.name,
#         Courses.start_date,
#         Courses.end_date,
#         Courses.learning_outcomes,
#         Courses.status,
#         Courses.image_url,
#         Courses.professor_id,
#         StudentCourses.completed_lessons,
#         StudentCourses.time_spent,
#         StudentCourses.assignments_done,
#         StudentCourses.last_accessed,
#         Student.id,
#         Student.name,
#         Student.email,
#         Student.avatar_url,
#         ProfessorAlias.name,
#         ProfessorAlias.email,
#         ProfessorAlias.avatar_url,
#     ]

#     order_conditions = {"asc": ["name"]}

#     courses = await student_controller.student_repository._get_many(
#         where_=where_conditions,
#         fields=select_fields,
#         join_=join_conditions,
#         order_=order_conditions,
#         group_by_=group_by_fields,
#     )

#     course_map = {}

#     for course in courses:
#         course_id = course.id

#         if course_id not in course_map:
#             course_map[course_id] = {
#                 "id": course.id,
#                 "name": course.name,
#                 "start_date": str(course.start_date),
#                 "end_date": str(course.end_date),
#                 "student_list": [],
#                 "learning_outcomes": course.learning_outcomes,
#                 "professor": ProfessorInformation(
#                     professor_id=course.professor_id,
#                     professor_name=course.professor_name,
#                     professor_email=course.professor_email,
#                     professor_avatar=str(course.professor_avatar),
#                 ),
#                 "status": course.status,
#                 "image": str(course.image_url),
#                 "percentage_complete": f"{(course.completed_lessons / course.total_lessons * 100) if course.total_lessons > 0 else 0:.0f}",
#                 "last_accessed": str(course.last_accessed),
#             }

#         course_map[course_id]["student_list"].append(
#             StudentList(
#                 student_id=course.student_id,
#                 student_name=course.student_name,
#                 student_email=course.student_email,
#                 student_avatar=str(course.student_avatar),
#             )
#         )
#     response_content = [GetCoursesResponse(**course_data) for course_data in course_map.values()]
#     total_rows = len(response_content)
#     total_pages = total_rows // request.page_size
#     if total_pages == 0:
#         total_pages = 1

#     response_content = response_content[request.offset : request.offset + request.page_size]
#     response = Ok(
#         data=GetCoursesPaginatedResponse(
#             content=response_content,
#             currentPage=(request.offset // request.page_size) + 1,
#             pageSize=request.page_size,
#             totalRows=total_rows,
#             totalPages=total_pages,
#         ),
#         message="Successfully fetched the courses.",
#     )

#     return response


# @router.get("/{courseId}/students/{studentId}/", response_model=Ok[GetCourseDetailResponse])
# async def get_course_for_student(
#     courseId: str,
#     studentId: str,
#     courses_controller: CoursesController = Depends(InternalProvider().get_courses_controller),
#     student_courses_controller: StudentCoursesController = Depends(InternalProvider().get_studentcourses_controller),
#     lessons_controller: LessonsController = Depends(InternalProvider().get_lessons_controller),
#     exercises_controller: ExercisesController = Depends(InternalProvider().get_exercises_controller),
#     student_lessons_controller: StudentLessonsController = Depends(InternalProvider().get_studentlessons_controller),
#     student_exercises_controller: StudentExercisesController = Depends(
#         InternalProvider().get_studentexercises_controller
#     ),
#     document_controller: DocumentsController = Depends(InternalProvider().get_documents_controller),
# ):
#     if not courseId or not studentId:
#         raise BadRequestException(message="Student ID and Course ID are required.")

#     student_course = await student_courses_controller.student_courses_repository.first(
#         where_=[and_(StudentCourses.student_id == studentId, StudentCourses.course_id == courseId)]
#     )
#     if not student_course:
#         raise BadRequestException(message="Student is not enrolled in this course.")

#     where_conditions = [StudentCourses.course_id == courseId, StudentCourses.student_id == studentId]
#     join_conditions = {
#         "student_courses": {"type": "left", "alias": "student_courses"},
#         "professor": {"type": "left", "alias": "professor_alias"},
#     }
#     select_fields = [
#         Courses.id.label("course_id"),
#         Courses.name.label("course_name"),
#         Courses.start_date.label("course_start_date"),
#         Courses.end_date.label("course_end_date"),
#         Courses.learning_outcomes.label("course_learning_outcomes"),
#         Courses.professor_id.label("course_professor_id"),
#         Courses.status.label("course_status"),
#         Courses.image_url.label("course_image_url"),
#         Professor.name.label("professor_name"),
#         Professor.email.label("professor_email"),
#         Professor.avatar_url.label("professor_avatar"),
#     ]

#     get_orther_course_data = await courses_controller.courses_repository._get_many(
#         where_=where_conditions,
#         fields=select_fields,
#         join_=join_conditions,
#     )

#     get_orther_course_data = get_orther_course_data[0]

#     lessons = await lessons_controller.lessons_repository.get_many(
#         where_=[Lessons.course_id == courseId],
#         order_={"asc": ["order"]},
#     )

#     lesson_ids = [lesson.id for lesson in lessons]
#     student_lessons = await student_lessons_controller.student_lessons_repository.get_many(
#         where_=[
#             and_(
#                 StudentLessons.student_id == studentId,
#                 StudentLessons.lesson_id.in_(lesson_ids),
#             )
#         ]
#     )
#     student_lessons_by_lesson = {sl.lesson_id: sl for sl in student_lessons}

#     exercises = await exercises_controller.exercises_repository.get_many(
#         where_=[Exercises.lesson_id.in_(lesson_ids)],
#     )
#     exercises_by_lesson = {}
#     for exercise in exercises:
#         exercises_by_lesson.setdefault(exercise.lesson_id, []).append(exercise)

#     exercise_ids = [exercise.id for exercise in exercises]
#     student_exercises = await student_exercises_controller.student_exercises_repository.get_many(
#         where_=[StudentExercises.student_id == studentId, StudentExercises.exercise_id.in_(exercise_ids)],
#     )
#     student_exercises_by_exercise = {se.exercise_id: se for se in student_exercises}

#     lesson_documents = await document_controller.documents_repository.get_many(
#         where_=[Documents.lesson_id.in_(lesson_ids)],
#     )
#     documents_by_lesson = {}
#     for document in lesson_documents:
#         documents_by_lesson.setdefault(document.lesson_id, []).append(document)

#     lessons_response: List[GetLessonsResponse] = []
#     for lesson in lessons:
#         student_lesson = student_lessons_by_lesson.get(lesson.id)
#         lesson_exercises = exercises_by_lesson.get(lesson.id, [])
#         lesson_documents = documents_by_lesson.get(lesson.id, [])

#         lessons_response.append(
#             GetLessonsResponse(
#                 id=lesson.id,
#                 title=lesson.title,
#                 description=lesson.description or "",
#                 bookmark=student_lesson.bookmark if student_lesson else False,
#                 order=lesson.order,
#                 exercises=[
#                     GetExercisesResponse(
#                         id=exercise.id,
#                         name=exercise.name,
#                         description=exercise.description or "",
#                         status=(
#                             student_exercises_by_exercise[exercise.id].status
#                             if exercise.id in student_exercises_by_exercise
#                             else "New"
#                         ),
#                         type=exercise.type,
#                     )
#                     for exercise in lesson_exercises
#                 ],
#                 documents=[
#                     GetDocumentsResponse(
#                         id=document.id,
#                         name=document.name,
#                         type=document.type,
#                         url=document.document_url,
#                     )
#                     for document in lesson_documents
#                 ],
#             )
#         )
#     response = GetCourseDetailResponse(
#         course_id=get_orther_course_data.course_id,
#         course_name=get_orther_course_data.course_name,
#         course_start_date=str(get_orther_course_data.course_start_date),
#         course_end_date=str(get_orther_course_data.course_end_date),
#         course_learning_outcomes=get_orther_course_data.course_learning_outcomes,
#         course_professor=ProfessorInformation(
#             professor_id=get_orther_course_data.course_professor_id,
#             professor_name=get_orther_course_data.professor_name,
#             professor_email=get_orther_course_data.professor_email,
#             professor_avatar=str(get_orther_course_data.professor_avatar),
#         ),
#         course_status=get_orther_course_data.course_status,
#         course_image=str(get_orther_course_data.course_image_url),
#         course_percentage_complete=f"{(student_course.completed_lessons / len(lessons) * 100):.0f}",
#         student_id=student_course.student_id,
#         course_last_accessed=str(student_course.last_accessed),
#         completed_lessons=student_course.completed_lessons,
#         time_spent=str(student_course.time_spent),
#         assignments_done=student_course.assignments_done,
#         lessons=lessons_response,
#     )
#     return Ok(data=response, message="Successfully fetched the course details.")


# @router.put("/{courseId}/students/{studentId}/lessons/{lessonId}/bookmark", response_model=Ok[bool])
# async def bookmark_lesson(
#     courseId: UUID,
#     studentId: UUID,
#     lessonId: UUID,
#     student_lessons_controller: StudentLessonsController = Depends(InternalProvider().get_studentlessons_controller),
# ):
#     if not lessonId or not courseId or not studentId:
#         raise BadRequestException(message="Student ID, Course ID, and Lesson ID are required.")

#     lesson = await student_lessons_controller.student_lessons_repository.first(
#         where_=[
#             StudentLessons.lesson_id == lessonId,
#             StudentLessons.student_id == studentId,
#             StudentLessons.course_id == courseId,
#         ]
#     )

#     if not lesson:
#         raise BadRequestException(message="Lesson not found.")

#     new_bookmark_status = not lesson.bookmark

#     updated_lesson = await student_lessons_controller.student_lessons_repository.update(
#         where_=[
#             StudentLessons.lesson_id == lessonId,
#             StudentLessons.student_id == studentId,
#             StudentLessons.course_id == courseId,
#         ],
#         attributes={"bookmark": new_bookmark_status},
#         commit=True,
#     )

#     if not updated_lesson:
#         raise Exception("Failed to update lesson bookmark status")

#     if updated_lesson.bookmark != new_bookmark_status:
#         raise Exception("Bookmark status was not updated correctly")

#     return Ok(
#         data=new_bookmark_status,
#         message="Successfully {} the lesson.".format(
#             "bookmarked" if new_bookmark_status else "removed the bookmark from"
#         ),
#     )

# @router.get(
#     "/{courseId}/students/{studentId}/lessons_recommendation/",
#     response_model=Ok[List[GetLessonsRecommendationResponse]],
# )
# async def get_lessons_recommendation(
#     courseId: UUID,
#     studentId: UUID,
#     learning_paths_controller: LearningPathsController = Depends(InternalProvider().get_learningpaths_controller),
#     recommend_lessons_controller: RecommendLessonsController = Depends(InternalProvider().get_recommendlessons_controller),
#     lessons_controller: LessonsController = Depends(InternalProvider().get_lessons_controller),
# ):
#     if not courseId or not studentId:
#         raise BadRequestException(message="Both Student ID and Course ID are required.")

#     # Tìm Learning Path dựa trên Student ID và Course ID
#     where_learning_path_conditions = [
#         LearningPaths.student_id == studentId,
#         LearningPaths.course_id == courseId,
#     ]
#     learning_path = await learning_paths_controller.learning_paths_repository.first(
#         where_=where_learning_path_conditions,
#         relations=[LearningPaths.recommend_lessons, LearningPaths.course],
#     )

#     if not learning_path:
#         raise NotFoundException(message="Learning path not found for the given student and course.")

#     # Truy xuất thông tin từ RecommendLessons
#     recommend_lessons = learning_path.recommend_lessons
#     course_name = learning_path.course.name if learning_path.course else "Unknown Course"

#     if not recommend_lessons:
#         raise NotFoundException(message="No recommended lessons found for the given learning path.")

#     # Chuẩn bị dữ liệu trả về
#     recommended_lessons: List[GetLessonsRecommendationResponse] = []
#     for recommend_lesson in recommend_lessons:
#         # Lấy thông tin từ bảng Lessons
#         lesson = await lessons_controller.lessons_repository.first(
#             where_=[Lessons.id == recommend_lesson.id]
#         )
#         if not lesson:
#             continue

#         recommended_lessons.append(
#             GetLessonsRecommendationResponse(
#                 course_id=courseId,
#                 course_name=course_name,
#                 lesson_id=lesson.id,
#                 title=lesson.title,
#                 description=lesson.description or "",
#                 order=lesson.order,
#                 bookmark=lesson.bookmark if hasattr(lesson, "bookmark") else False,
#                 status=recommend_lesson.status,
#             )
#         )
    
#    return Ok(data=recommended_lessons, message="Successfully fetched the recommended lessons.")


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
        print("Your account is not authorized. Please log in again.")
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    
    user = await admin_controller.admin_repository.first(where_=[Admin.id == user_id])
    if not user:
        print("Your account is not allowed to create a course.")
        raise NotFoundException(message="Your account is not allowed to create a course.")
    
    if not request.headers or not request.courses:
        print("Headers and Courses are required.")
        raise BadRequestException(message="Headers and Courses are required.")

    if not request.headers == expectedHeaders:
        print(f"Headers must match the fixed values: {expectedHeaders}")
        raise BadRequestException(message="Headers must match the fixed values: {expectedHeaders}")

    if len(request.courses) == 0:
        print("At least one course is required.")
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
            print("Failed to create course")
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
            where_=[Professor.email.in_(professor_emails)],
            fields=[Professor.id, Professor.email]
        )
        
        professor_id_map = {prof['email']: prof['id'] for prof in professors}

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
            attributes_list=courses_attributes,
            commit=True
        )
        if not create_courses:
            raise Exception("Failed to create courses")

        courses_response = []
        for created_course, request_course in zip(create_courses, request.courses):

            student_emails = request_course.student_list
            students = await student_controller.student_repository._get_many(
                where_=[Student.email.in_(student_emails)],
                fields=[Student.id, Student.email]
            )

            student_courses_attributes = [
                {
                    "student_id": student['id'],
                    "course_id": created_course.id,
                }
                for student in students
            ]

            create_student_courses = await student_courses_controller.student_courses_repository.create_many(
                attributes_list=student_courses_attributes,
                commit=True
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
                "student_courses_list": student_courses_response
            }
            courses_response.append(course_response)

        return Ok(data=courses_response, message="Successfully created the courses.")
        
# @router.put("/learning_outcomes", response_model=Ok[PutLearningOutcomesCoursesResponse])
# async def bookmark_lesson(
#     body: PutLearningOutcomesCoursesRequest,
#     courses_controller: CoursesController = Depends(InternalProvider().get_courses_controller),
# ):

#     course = await courses_controller.courses_repository.first(
#         where_=[
#             Courses.id == body.course_id,
#         ]
#     )

#     if not course:
#         raise BadRequestException(message="Course not found.")

#     learning_outcomes = body.learning_outcomes

#     updated_course = await courses_controller.courses_repository.update(
#         where_=[
#             Courses.id == body.course_id,
#         ],
#         attributes={"learning_outcomes": learning_outcomes},
#         commit=True,
#     )

#     if not updated_course:
#         raise Exception("Failed to update course learning outcomes")

#     return Ok(
#         data=PutLearningOutcomesCoursesResponse(
#             course_id=updated_course.id,
#             learning_outcomes=updated_course.learning_outcomes,
#         ),
#         message="Successfully updated the course learning outcomes.",
#     )
