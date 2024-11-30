from core.repository import BaseRepository
from machine.models import Lessons, StudentLessons, Exercises, Documents
from sqlalchemy.orm import aliased

class LessonsRepository(BaseRepository[Lessons]):
    def _join_student_lessons(self, query, join_params):
        join_type = join_params.get("type", "inner")
        alias = join_params.get("alias", aliased(StudentLessons))

        if join_type == "left":
            return query.outerjoin(alias, alias.lesson_id == self.model_class.id)
        return query.join(alias, alias.lesson_id == self.model_class.id)

    def _join_exercises(self, query, join_params):
        join_type = join_params.get("type", "inner")
        alias = join_params.get("alias", aliased(Exercises))

        if join_type == "left":
            return query.outerjoin(alias, alias.lesson_id == self.model_class.id)
        return query.join(alias, alias.lesson_id == self.model_class.id)

    def _join_documents(self, query, join_params):
        join_type = join_params.get("type", "inner")
        alias = join_params.get("alias", aliased(Documents))

        if join_type == "left":
            return query.outerjoin(alias, alias.lesson_id == self.model_class.id)
        return query.join(alias, alias.lesson_id == self.model_class.id)

