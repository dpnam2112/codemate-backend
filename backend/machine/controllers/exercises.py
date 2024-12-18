from core.controller import BaseController
from machine.models import Exercises
from machine.repositories import ExercisesRepository


class ExercisesController(BaseController[Exercises]):
    def __init__(self, exercises_repository: ExercisesRepository):
        super().__init__(model_class=Exercises, repository=exercises_repository)
        self.exercises_repository = exercises_repository