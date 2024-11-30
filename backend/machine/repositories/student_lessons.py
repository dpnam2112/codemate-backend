from sqlalchemy import Select
from core.repository import BaseRepository
from machine.models import StudentLessons, Lessons, Courses

class StudentLessonsRepository(BaseRepository[StudentLessons]):
    def _join_lessons(self, query: Select, join_params: dict) -> Select:
        join_type = join_params.get('type', 'inner')
        alias = join_params.get('table', Lessons)
        
        if join_type == 'left':
            return query.outerjoin(alias, alias.id == self.model_class.lesson_id)
        return query.join(alias, alias.id == self.model_class.lesson_id)
    def _join_courses(self, query: Select, join_params: dict) -> Select:
        join_type = join_params.get('type', 'inner')
        alias = join_params.get('table', Courses)
        
        if join_type == 'left':
            return query.outerjoin(alias, alias.id == Lessons.course_id)
        return query.join(alias, alias.id == Lessons.course_id)
