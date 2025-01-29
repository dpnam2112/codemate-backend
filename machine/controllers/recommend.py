from typing import Optional
from uuid import UUID
from core.controller import BaseController
from core.exceptions.base import NotFoundException
from machine.models import Modules, RecommendDocuments, RecommendLessons, LearningPaths, RecommendQuizzes
from machine.repositories import ModulesRepository, RecommendDocumentsRepository,RecommendLessonsRepository,LearningPathsRepository, RecommendQuizzesRepository
from machine.schemas.responses.learning_path import ModuleDTO, RecommendedLessonDTO
from core.db import Transactional
from sqlalchemy.orm import selectinload
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
            relations=[LearningPaths.recommend_lessons]
        )
        if lp is None: raise NotFoundException(message="learning path is not created.")
        return lp

    async def get_recommended_lessons(self, user_id: UUID, course_id: UUID, expand: Optional[str] = None) -> list[RecommendedLessonDTO]:


        # Prepare options for relationship loading
        options_ = [
            selectinload(LearningPaths.recommend_lessons)
        ]

        if expand == "modules":
            options_.append(selectinload(LearningPaths.recommend_lessons).selectinload(RecommendLessons.modules))

        # Fetch the learning path with the specified options
        learning_path = await self.repository.first(
            where_=[LearningPaths.course_id == course_id, LearningPaths.student_id == user_id],
            options_=options_
        )

        if learning_path is None:
            raise NotFoundException(message="Learning path not found.")

        # Convert to DTO using model_validate
        lessons = [
            RecommendedLessonDTO.model_validate({
                **lesson.__dict__,
                "modules": [
                    ModuleDTO.model_validate(module)
                    for module in lesson.modules
                ] if expand == "modules" else None
            })
            for lesson in learning_path.recommend_lessons
        ]

        return lessons

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

# class QuizExercisesController(BaseController[QuizExercises]):
#     def __init__(self, quiz_exercises_repository: QuizExercisesRepository):
#         super().__init__(model_class=QuizExercises, repository=quiz_exercises_repository)
#         self.quiz_exercises_repository = quiz_exercises_repository

class RecommendDocumentsController(BaseController[RecommendDocuments]):
    def __init__(self, recommend_documents_repository: RecommendDocumentsRepository):
        super().__init__(model_class=RecommendDocuments, repository=recommend_documents_repository)
        self.recommend_documents_repository = recommend_documents_repository
