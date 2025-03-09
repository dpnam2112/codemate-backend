from core.controller import BaseController
from machine.models import Courses, StudentExercises
from machine.repositories import CoursesRepository, StudentExercisesRepository   


class CoursesController(BaseController[Courses]):
    def __init__(self, courses_repository: CoursesRepository):
        super().__init__(model_class=Courses, repository=courses_repository)
        self.courses_repository = courses_repository
        
class StudentExercisesController(BaseController[StudentExercises]):
    def __init__(self, student_exercises_repository: StudentExercisesRepository):
        super().__init__(model_class=StudentExercises, repository=student_exercises_repository)
        self.student_exercises_repository = student_exercises_repository