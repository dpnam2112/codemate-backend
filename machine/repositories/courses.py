from sqlalchemy import Select
from core.repository.base import BaseRepository
from machine.models import Courses, StudentCourses, Lessons, Professor, Student

class CoursesRepository(BaseRepository[Courses]):
    def _join_student_courses(self, query: Select, join_params: dict) -> Select:
        join_type = join_params.get('type', 'inner')
        alias = join_params.get('table', StudentCourses)
        
        if join_type == 'left':
            return query.outerjoin(alias, alias.course_id == self.model_class.id)
        return query.join(alias, alias.course_id == self.model_class.id)

    def _join_professor(self, query: Select, join_params: dict) -> Select:
        join_type = join_params.get('type', 'inner')
        table = join_params.get('table', Professor)
        
        if join_type == 'left':
            return query.outerjoin(table, self.model_class.professor_id == table.id)
        return query.join(table, self.model_class.professor_id == table.id)

    def _join_lessons(self, query: Select, join_params: dict) -> Select:
        join_type = join_params.get('type', 'inner')
        alias = join_params.get('table', Lessons)
        
        if join_type == 'left':
            return query.outerjoin(alias, alias.course_id == self.model_class.id)
        return query.join(alias, alias.course_id == self.model_class.id)