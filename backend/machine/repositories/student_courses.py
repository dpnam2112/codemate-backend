from sqlalchemy import Select
from core.repository import BaseRepository
from machine.models import StudentCourses, Courses, Student
from sqlalchemy.orm import aliased

class StudentCoursesRepository(BaseRepository[StudentCourses]):
    def _join_courses(self, query: Select, join_params: dict) -> Select:
        join_type = join_params.get('type', 'inner')
        alias = join_params.get('table', Courses)

        if join_type == 'left':
            return query.outerjoin(alias, alias.id == self.model_class.course_id)
        return query.join(alias, alias.id == self.model_class.course_id)

    def _join_student(self, query: Select, join_params: dict) -> Select:
        join_type = join_params.get('type', 'inner')
        alias = join_params.get('table', Student)

        query = query.select_from(StudentCourses)  

        if join_type == 'left':
            return query.outerjoin(alias, alias.id == StudentCourses.student_id)
        return query.join(alias, alias.id == StudentCourses.student_id)
