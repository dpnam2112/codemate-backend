from uuid import UUID
from pydantic import BaseModel
from typing import List
from core.repository.enum import StatusType

class StudentList(BaseModel):
    student_id: UUID
    student_name: str
    student_email: str

class ProfessorInformation(BaseModel):
    professor_id: UUID
    professor_name: str
    professor_email: str
class GetCoursesResponse(BaseModel):
    id: UUID
    name: str
    start_date: str
    end_date: str
    student_list: List[StudentList]
    learning_outcomes: List[str]
    professor: ProfessorInformation
    status: StatusType
    image: str
    percentage_complete: str
    last_accessed: str
 
class GetCoursesPaginatedResponse(BaseModel):
    content: List[GetCoursesResponse]
    currentPage: int
    pageSize: int
    totalRows: int
    totalPages: int
