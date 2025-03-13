from core.controller import BaseController
from machine.models import Lessons, Documents, ExtractedText
from machine.repositories import LessonsRepository, DocumentsRepository, ExtractedTextRepository


class LessonsController(BaseController[Lessons]):
    def __init__(self, lessons_repository: LessonsRepository):
        super().__init__(model_class=Lessons, repository=lessons_repository)
        self.lessons_repository = lessons_repository
        
class DocumentsController(BaseController[Documents]):
    def __init__(self, documents_repository: DocumentsRepository):
        super().__init__(model_class=Documents, repository=documents_repository)
        self.documents_repository = documents_repository
        
        
class ExtractedTextController(BaseController[ExtractedText]):
    def __init__(self, extracted_text_repository: ExtractedTextRepository):
        super().__init__(model_class=ExtractedText, repository=extracted_text_repository)
        self.extracted_text_repository = extracted_text_repository