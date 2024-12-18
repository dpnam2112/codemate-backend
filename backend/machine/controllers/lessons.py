from core.controller import BaseController
from machine.models import Lessons, Documents
from machine.repositories import LessonsRepository, DocumentsRepository


class LessonsController(BaseController[Lessons]):
    def __init__(self, lessons_repository: LessonsRepository):
        super().__init__(model_class=Lessons, repository=lessons_repository)
        self.lessons_repository = lessons_repository
        
class DocumentsController(BaseController[Documents]):
    def __init__(self, documents_repository: DocumentsRepository):
        super().__init__(model_class=Documents, repository=documents_repository)
        self.documents_repository = documents_repository