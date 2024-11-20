from core.controller import BaseController
from machine.models import Courses
from machine.repositories import CoursesRepository


class CoursesController(BaseController[Courses]):
    def __init__(self, courses_repository: CoursesRepository):
        super().__init__(model_class=Courses, repository=courses_repository)
        self.courses_repository = courses_repository