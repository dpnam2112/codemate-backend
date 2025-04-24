from sqlalchemy import Select
from core.repository.base import BaseRepository
from machine.models import Feedback, Student, Courses

class FeedbackRepository(BaseRepository[Feedback]):
    def _join_student(self, query: Select, join_params: dict) -> Select:
        join_type = join_params.get('type', 'inner')
        alias = join_params.get('table', Student)
        
        if join_type == 'left':
            return query.outerjoin(alias, alias.id == self.model_class.student_id)
        return query.join(alias, alias.id == self.model_class.student_id)
    def _join_course(self, query: Select, join_params: dict) -> Select:
        join_type = join_params.get('type', 'inner')
        alias = join_params.get('table', Courses)
        
        if join_type == 'left':
            return query.outerjoin(alias, alias.id == self.model_class.course_id)
        return query.join(alias, alias.id == self.model_class.course_id)