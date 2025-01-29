from core.repository import BaseRepository
from sqlalchemy.sql.expression import Select
from machine.models import Student, Professor, Admin, StudentCourses, Courses


class StudentRepository(BaseRepository[Student]):
    def _join_student_courses(self, query: Select, join_params: dict) -> Select:
        """
        Joins the Students table with the StudentCourses table.
        """
        join_type = join_params.get("type", "inner")
        alias = join_params.get("table", StudentCourses)

        if join_type == "left":
            return query.outerjoin(alias, alias.student_id == self.model_class.id)
        return query.join(alias, alias.student_id == self.model_class.id)

    def _join_courses(self, query: Select, join_params: dict) -> Select:
        """
        Joins the Students table with the Courses table via the StudentCourses table.
        """
        join_type = join_params.get("type", "inner")
        alias = join_params.get("table", Courses)

        if join_type == "left":
            return query.outerjoin(alias, alias.id == StudentCourses.course_id)
        return query.join(alias, alias.id == StudentCourses.course_id)


class ProfessorRepository(BaseRepository[Professor]):
    def _join_courses(self, query: Select, join_params: dict) -> Select:
        """
        Joins the Professors table with their Courses.
        """
        join_type = join_params.get("type", "inner")
        alias = join_params.get("table", Courses)

        if join_type == "left":
            return query.outerjoin(alias, alias.professor_id == self.model_class.id)
        return query.join(alias, alias.professor_id == self.model_class.id)

    def _join_student_courses(self, query: Select, join_params: dict) -> Select:
        """
        Joins the Professors table with StudentCourses via Courses.
        """
        join_type = join_params.get("type", "inner")
        alias = join_params.get("table", StudentCourses)

        query = self._join_courses(query, {"type": join_type})
        
        if join_type == "left":
            return query.outerjoin(alias, alias.course_id == Courses.id)
        return query.join(alias, alias.course_id == Courses.id)


class AdminRepository(BaseRepository[Admin]):
    """
    Repository for Admin model operations.
    No specific join methods needed for basic admin functionality.
    Add methods here if admin-specific queries are needed.
    """
    pass