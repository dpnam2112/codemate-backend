from core.controller import BaseController
from machine.models import Modules,QuizExercises,Documents
from machine.repositories import ModulesRepository,QuizExercisesRepository,DocumentsRepository

class ModulesController(BaseController[Modules]):
    def __init__(self, modules_repository: ModulesRepository):
        super().__init__(model_class=Modules, repository=modules_repository)
        self.modules_repository = modules_repository
class QuizExercisesController(BaseController[QuizExercises]):
    def __init__(self, quiz_exercises_repository: QuizExercisesRepository):
        super().__init__(model_class=QuizExercises, repository=quiz_exercises_repository)
        self.quiz_exercises_repository = quiz_exercises_repository
class DocumentsController(BaseController[Documents]):
    def __init__(self, documents_repository: DocumentsRepository):
        super().__init__(model_class=Documents, repository=documents_repository)
        self.documents_repository = documents_repository