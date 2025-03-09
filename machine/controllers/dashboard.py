from core.controller import BaseController
from machine.models import StudentCourses, Activities
from machine.repositories import StudentCoursesRepository, ActivitiesRepository

class StudentCoursesController(BaseController[StudentCourses]):
    def __init__(self, student_courses_repository: StudentCoursesRepository):
        super().__init__(model_class=StudentCourses, repository=student_courses_repository)
        self.student_courses_repository = student_courses_repository
        
class ActivitiesController(BaseController[Activities]):
    def __init__(self, activities_repository: ActivitiesRepository):
        super().__init__(model_class=Activities, repository=activities_repository)
        self.activities_repository = activities_repository