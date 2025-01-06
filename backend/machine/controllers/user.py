from core.controller import BaseController
from machine.models import Student, Professor, Admin 
from machine.repositories import StudentRepository, ProfessorRepository, AdminRepository


class StudentController(BaseController[Student]):
    def __init__(self, student_repository: StudentRepository):
        super().__init__(model_class=Student, repository=student_repository)
        self.student_repository = student_repository
    def get_student_by_email(self, email: str):
        return self.student_repository.first(where_=[Student.email == email])


class ProfessorController(BaseController[Professor]):
    def __init__(self, professor_repository: ProfessorRepository):
        super().__init__(model_class=Professor, repository=professor_repository)
        self.professor_repository = professor_repository
    def get_professor_by_email(self, email: str):
        return self.professor_repository.first(where_=[Professor.email == email])


class AdminController(BaseController[Admin]):
    def __init__(self, admin_repository: AdminRepository):
        super().__init__(model_class=Admin, repository=admin_repository)
        self.admin_repository = admin_repository
    def get_admin_by_email(self, email: str):
        return self.admin_repository.first(where_=[Admin.email == email])