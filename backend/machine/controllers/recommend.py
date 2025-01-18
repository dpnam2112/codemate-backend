from core.controller import BaseController
from machine.models import Modules,RecommendQuizzes,RecommendDocuments, RecommendLessons, LearningPaths
from machine.repositories import ModulesRepository,RecommendQuizzesRepository, RecommendDocumentsRepository,RecommendLessonsRepository,LearningPathsRepository

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
class RecommendQuizzesController(BaseController[RecommendQuizzes]):
    def __init__(self, recommend_quizzes_repository: RecommendQuizzesRepository):
        super().__init__(model_class=RecommendQuizzes, repository=recommend_quizzes_repository)
        self.recommend_quizzes_repository = recommend_quizzes_repository
class RecommendDocumentsController(BaseController[RecommendDocuments]):
    def __init__(self, recommend_documents_repository: RecommendDocumentsRepository):
        super().__init__(model_class=RecommendDocuments, repository=recommend_documents_repository)
        self.recommend_documents_repository = recommend_documents_repository