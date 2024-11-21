from core.controller import BaseController
from machine.models import Lessons
from machine.repositories import LessonsRepository


class LessonsController(BaseController[Lessons]):
    def __init__(self, lessons_repository: LessonsRepository):
        super().__init__(model_class=Lessons, repository=lessons_repository)
        self.lessons_repository = lessons_repository