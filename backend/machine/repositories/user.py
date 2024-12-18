from core.repository import BaseRepository
from machine.models import User, StudentCourses, Courses
from sqlalchemy.sql.expression import Select


class UserRepository(BaseRepository[User]):
    def _join_student_courses(self, query: Select, join_params: dict) -> Select:
        """
        Joins the Users table with the StudentCourses table.
        """
        join_type = join_params.get("type", "inner")
        alias = join_params.get("table", StudentCourses)

        if join_type == "left":
            return query.outerjoin(alias, alias.student_id == self.model_class.id)
        return query.join(alias, alias.student_id == self.model_class.id)
    def _join_courses(self, query: Select, join_params: dict) -> Select:
        """
        Joins the Users table with the Courses table via the StudentCourses table.
        """
        join_type = join_params.get("type", "inner")
        alias = join_params.get("table", Courses)

        if join_type == "left":
            return query.outerjoin(alias, alias.id == StudentCourses.course_id)
        return query.join(alias, alias.id == StudentCourses.course_id)
    def _join_professor(self, query: Select, join_params: dict) -> Select:
        """
        Joins the Users table with the Professor (Users table).
        """
        join_type = join_params.get("type", "inner")
        alias = join_params.get("table", User)

        if join_type == "left":
            return query.outerjoin(alias, alias.id == Courses.professor_id)
        return query.join(alias, alias.id == Courses.professor_id)


