from core.controller import BaseController
from machine.models import Modules,QuizExercises,RecommendDocuments, RecommendLessons, LearningPaths
from machine.repositories import ModulesRepository,QuizExercisesRepository, RecommendDocumentsRepository,RecommendLessonsRepository,LearningPathsRepository

class LearningPathsController(BaseController[LearningPaths]):
    def __init__(self, learning_paths_repository: LearningPathsRepository):
        super().__init__(model_class=LearningPaths, repository=learning_paths_repository)
        self.learning_paths_repository = learning_paths_repository
class RecommendLessonsController(BaseController[RecommendLessons]):
    def __init__(self, recommend_lessons_repository: RecommendLessonsRepository):
        super().__init__(model_class=RecommendLessons, repository=recommend_lessons_repository)
        self.recommend_lessons_repository = recommend_lessons_repository
class ModulesController(BaseController[Modules]):
    def __init__(self, modules_repository: ModulesRepository):
        super().__init__(model_class=Modules, repository=modules_repository)
        self.modules_repository = modules_repository
class QuizExercisesController(BaseController[QuizExercises]):
    def __init__(self, quiz_exercises_repository: QuizExercisesRepository):
        super().__init__(model_class=QuizExercises, repository=quiz_exercises_repository)
        self.quiz_exercises_repository = quiz_exercises_repository
class RecommendDocumentsController(BaseController[RecommendDocuments]):
    def __init__(self, recommend_documents_repository: RecommendDocumentsRepository):
        super().__init__(model_class=RecommendDocuments, repository=recommend_documents_repository)
        self.recommend_documents_repository = recommend_documents_repository