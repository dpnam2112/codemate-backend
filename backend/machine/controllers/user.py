from core.controller import BaseController
from machine.models import Student, Professor, Admin 
from machine.repositories import StudentRepository, ProfessorRepository, AdminRepository


class StudentController(BaseController[Student]):
    def __init__(self, student_repository: StudentRepository):
        super().__init__(model_class=Student, repository=student_repository)
        self.student_repository = student_repository
    

class ProfessorController(BaseController[Professor]):
    def __init__(self, professor_repository: ProfessorRepository):
        super().__init__(model_class=Professor, repository=professor_repository)
        self.professor_repository = professor_repository
   

class AdminController(BaseController[Admin]):
    def __init__(self, admin_repository: AdminRepository):
        super().__init__(model_class=Admin, repository=admin_repository)
        self.admin_repository = admin_repository
    