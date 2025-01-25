# import os
# from data.constant import *
# from fastapi import APIRouter, Depends
# from dotenv import load_dotenv
# from fastapi.security import OAuth2PasswordBearer
# from machine.controllers import *
# from machine.providers import InternalProvider
# from core.utils.auth_utils import verify_token
# from core.exceptions import *
# from machine.models import *
# from sqlalchemy.sql import func, and_, or_

# load_dotenv()
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# router = APIRouter(prefix="/progress_tracking", tags=["progress_tracking"])


# @router.get("/bar-chart-module-lesson/{courseId}")
# async def get_bar_chart_module_lesson(
#     courseId: str,
#     token: str = Depends(oauth2_scheme),
#     student_controller: StudentController = Depends(InternalProvider.get_student_controller),
#     course_controller: CoursesController = Depends(InternalProvider.get_courses_controller),
#     learning_path_controller: LearningPathsController = Depends(InternalProvider.get_learningpaths_controller),
#     recommend_lesson_controller: RecommendLessonsController = Depends(InternalProvider.get_recommendlessons_controller),
#     modules_controller: ModulesController = Depends(InternalProvider.get_modules_controller),
#     quiz_exercises_controller: QuizExercisesController = Depends(InternalProvider.get_quizexercises_controller),
#     lessons_controller: LessonsController = Depends(InternalProvider.get_lessons_controller),
# ):
#     payload = verify_token(token)
#     user_id = payload.get("sub")

#     if not user_id:
#         raise UnauthorizedException("Invalid Token")

#     checkRole = any(
#         user_id in progress_tracking_test_student_child.id
#         for progress_tracking_test_student_child in progress_tracking_test_student
#     )  # await student_controller.student_repository.first(where_=Student.id == user_id)

#     # if not checkRole:
#     #     raise BadRequestException("You are not a student")
#     learning_path_id = None  # await learning_path_controller.learningpaths_repository.first(where=and_(LearningPaths.student_id == user_id, LearningPaths.course_id == courseId))
#     for learningpath in progress_tracking_test_learning_path:
#         if learningpath.course_id == courseId and learningpath.student_id == user_id:
#             learning_path_id = learningpath.id
#             break

#     # if not learning_path_id:
#     #     raise NotFoundException("You have not had any learning path for this course")

#     getRecommendLesson = await recommend_lesson_controller.recommend_lessons_repository._get_many(
#         where_=LearningPaths.id == learning_path_id
#     )
    
#     getModules = []
#     for recommend_lesson in getRecommendLesson:
#         getModule = await modules_controller.modules_repository._get_many(
#             where_=Modules.recommend_lesson_id == recommend_lesson.id
#         )
#         if not getModule:
#             raise NotFoundException(f"Module with recommend_lesson_id = {recommend_lesson.id} not found")
#         getModule_map = []
#         for module in getModule:
#             getModule_map.append(
#                 {
#                     "id": module.id,
#                     "module_title": module.title,
#                     "module_objectives": module.objectives,
#                     "last_accessed": module.last_accessed,
#                     "recommend_lesson_id": recommend_lesson.id,
#                     "learning_path_id": recommend_lesson.learning_path_id,
#                     "lesson_id": recommend_lesson.lesson_id,
#                     "recommend_lesson_progress": recommend_lesson.progress,
#                     "recommended_content": recommend_lesson.recommended_content,
#                     "recommend_lesson_explain": recommend_lesson.explain,
#                     "recommend_lesson_status": recommend_lesson.status,
#                 }
#             )
#             getModules.append(getModule_map)
            
#     getQuizExercises = []
#     for module in getModules:
#         getQuizExercise = await quiz_exercises_controller.quiz_exercises_repository._get_many(
#             where_=QuizExercises.module_id == module.id
#         )
#         if not getQuizExercise:
#             raise NotFoundException(f"Quiz Exercise with module_id = {module.id} not found")
#         getQuizExercise_map = []
#         for quiz in getQuizExercise:
#             getQuizExercise_map.append(
#                 {
#                     "id": quiz.id,
#                     "module_id": quiz.module_id,
#                     "title": quiz.title,
#                     "description": quiz.description,
#                     "order": quiz.order,
#                     "learning_outcomes": quiz.learning_outcomes,
#                     "quiz_exercise_id": quiz.id,
#                     "progress": quiz.progress,
#                     "recommended_content": quiz.recommended_content,
#                     "explain": quiz.explain,
#                     "status": quiz.status,
#                 }
#             )
#             getQuizExercises.append(getQuizExercise_map)
#     # getLessons = []
#     # for lesson in getRecommendLesson:
#     #     getLesson = await lessons_controller.lessons_repository.first(where_=Lessons.id == lesson.lesson_id)
#     #     if not getLesson:
#     #         raise NotFoundException(f"Lesson with {lesson.lesson_id} not found")
#     #     getLessons.append(
#     #         {
#     #             "id": getLesson.id,
#     #             "course_id": getLesson.course_id,
#     #             "title": getLesson.title,
#     #             "description": getLesson.description,
#     #             "order": getLesson.order,
#     #             "learning_outcomes": getLesson.learning_outcomes,
#     #             "recommend_lesson_id": lesson.id,
#     #             "learning_path_id": lesson.learning_path_id,
#     #             "lesson_id": lesson.lesson_id,
#     #             "progress": lesson.progress,
#     #             "recommended_content": lesson.recommended_content,
#     #             "explain": lesson.explain,
#     #             "status": lesson.status,
#     #         }
#     #     )
