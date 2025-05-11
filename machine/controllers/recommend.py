from typing import Optional
from uuid import UUID
from core.controller import BaseController
from core.exceptions.base import NotFoundException
from machine.models import Modules, RecommendDocuments, RecommendLessons, LearningPaths, RecommendQuizzes, Lessons, RecommendQuizQuestion
from machine.repositories import ModulesRepository, RecommendDocumentsRepository, RecommendLessonsRepository, LearningPathsRepository, RecommendQuizzesRepository, RecommendQuizQuestionRepository
from machine.schemas.responses.learning_path import ModuleDTO, RecommendedLessonDTO
from core.db import Transactional
from sqlalchemy.orm import selectinload
from datetime import timedelta
def format_timedelta(td: timedelta) -> str:
    if td is None:
        return None
    total_seconds = int(td.total_seconds())
    days = total_seconds // (24 * 3600)
    hours = (total_seconds % (24 * 3600)) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    parts = []
    if days > 0:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds > 0 or not parts:
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
    return " ".join(parts)
class LearningPathsController(BaseController[LearningPaths]):
    def __init__(
        self,
        learning_paths_repository: LearningPathsRepository,
        recommended_lesson_repository: RecommendLessonsRepository
    ):
        super().__init__(model_class=LearningPaths, repository=learning_paths_repository)
        self.learning_paths_repository = learning_paths_repository
        self.recommended_lesson_repository = recommended_lesson_repository

    async def get_learning_path(self, user_id: UUID, course_id: UUID):
        lp = await self.repository.first(
            where_=[LearningPaths.course_id == course_id, LearningPaths.student_id == user_id],
            relations=[LearningPaths.recommend_lessons],
            order_={"desc": ["version"]}
        )
        # if lp is None: raise NotFoundException(message="learning path is not created.")
        return lp

    async def get_recommended_lessons(self, user_id: UUID, course_id: UUID, expand: Optional[str] = None) -> list[RecommendedLessonDTO]:
        # Prepare options for relationship loading
        options_ = [
            selectinload(LearningPaths.recommend_lessons)
            .selectinload(RecommendLessons.lesson)  # Load the lesson relationship
        ]

        if expand == "modules":
            options_.append(
                selectinload(LearningPaths.recommend_lessons)
                .selectinload(RecommendLessons.modules)
            )
        
        learning_path_list = await self.learning_paths_repository.get_many(
            where_=[LearningPaths.course_id == course_id, LearningPaths.student_id == user_id],
            order_={"desc": ["version"]},
        )
        if not learning_path_list:
            raise NotFoundException(message="Learning path not found.")
        
        learning_path = await self.learning_paths_repository.first(
            where_=[LearningPaths.course_id == course_id, LearningPaths.student_id == user_id, LearningPaths.version == learning_path_list[0].version],
            options_=options_
        )
        if learning_path is None:
            raise NotFoundException(message="Learning path not found.")
        
        # Convert to DTO using model_validate
        lessons = [
            RecommendedLessonDTO.model_validate({
                **lesson.__dict__,
                "lesson_title": lesson.lesson.title if lesson.lesson else None, 
                "time_spent": format_timedelta(lesson.time_spent) if lesson.time_spent else None,
                "modules": [
                    ModuleDTO.model_validate(module)
                    for module in lesson.modules
                ] if expand == "modules" else None,
            })
            for lesson in learning_path.recommend_lessons
        ]

        return {
            "student_goal": learning_path.objective,
            "lessons": lessons
        }
    async def get_recommended_lessons_by_learning_path_id(self, learning_path_id: UUID) -> list[RecommendedLessonDTO]:
        """
        Retrieve all recommended lessons and their associated modules for a given learning_path_id.
        
        Args:
            learning_path_id (UUID): The ID of the LearningPath to query.
        
        Returns:
            list[RecommendedLessonDTO]: A list of RecommendedLessonDTO objects with module details.
        
        Raises:
            NotFoundException: If the learning path or no recommended lessons are found.
        """
        # Fetch the LearningPath with its recommend_lessons and modules eagerly loaded
        learning_path = await self.learning_paths_repository.first(
            where_=[LearningPaths.id == learning_path_id],
            options_=[
                selectinload(LearningPaths.recommend_lessons)
                .selectinload(RecommendLessons.modules)  # Eagerly load modules through recommend_lessons
            ]
        )

        if not learning_path:
            raise NotFoundException(message="Learning path not found.")
        
        if not learning_path.recommend_lessons:
            raise NotFoundException(message="No recommended lessons found for the specified learning path.")

        # Convert to DTOs
        lessons_dto = [
            RecommendedLessonDTO.model_validate({
                **lesson.__dict__,
                "modules": [ModuleDTO.model_validate(module) for module in lesson.modules]
            })
            for lesson in learning_path.recommend_lessons
        ]

        return lessons_dto

    @Transactional()
    async def delete_learning_path(self, user_id: UUID, course_id: UUID) -> None:
        # Fetch the learning path
        learning_path = await self.repository.first(
            where_=[LearningPaths.course_id == course_id, LearningPaths.student_id == user_id]
        )
        if not learning_path:
            raise NotFoundException(message="Learning path not found.")
        
        # Delete the learning path
        await self.repository.session.delete(learning_path)


class RecommendLessonsController(BaseController[RecommendLessons]):
    def __init__(self, recommend_lessons_repository: RecommendLessonsRepository):
        super().__init__(model_class=RecommendLessons, repository=recommend_lessons_repository)
        self.recommend_lessons_repository = recommend_lessons_repository

class ModulesController(BaseController[Modules]):
    def __init__(self, modules_repository: ModulesRepository):
        super().__init__(model_class=Modules, repository=modules_repository)
        self.modules_repository = modules_repository
class RecommendQuizzesController(BaseController[RecommendQuizzes]):
    def __init__(self, recommend_quizzes_repository: RecommendQuizzesRepository):
        super().__init__(model_class=RecommendQuizzes, repository=recommend_quizzes_repository)
        self.recommend_quizzes_repository = recommend_quizzes_repository
class RecommendQuizQuestionController(BaseController[RecommendQuizQuestion]):
    def __init__(self, recommend_quiz_question_repository: RecommendQuizQuestionRepository):
        super().__init__(model_class=RecommendQuizQuestion, repository=recommend_quiz_question_repository)
        self.recommend_quiz_question_repository = recommend_quiz_question_repository
# class QuizExercisesController(BaseController[QuizExercises]):
#     def __init__(self, quiz_exercises_repository: QuizExercisesRepository):
#         super().__init__(model_class=QuizExercises, repository=quiz_exercises_repository)
#         self.quiz_exercises_repository = quiz_exercises_repository

class RecommendDocumentsController(BaseController[RecommendDocuments]):
    def __init__(self, recommend_documents_repository: RecommendDocumentsRepository):
        super().__init__(model_class=RecommendDocuments, repository=recommend_documents_repository)
        self.recommend_documents_repository = recommend_documents_repository
