from core.controller import BaseController
from machine.models import StudentCourses
from typing import Optional
from machine.repositories import StudentCoursesRepository

class DashboardController(BaseController[StudentCourses]):
    def __init__(self, student_courses_repository: StudentCoursesRepository):
        super().__init__(model_class=StudentCourses, repository=student_courses_repository)
        self.student_courses_repository = student_courses_repository