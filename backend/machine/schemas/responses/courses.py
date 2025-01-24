from uuid import UUID
from pydantic import BaseModel
from typing import List, Optional
from core.repository.enum import *

class StudentList(BaseModel):
    student_id: UUID
    student_name: str
    student_email: str
    student_avatar: str

class ProfessorInformation(BaseModel):
    professor_id: UUID
    professor_name: str
    professor_email: str
    professor_avatar: str
class GetCoursesResponse(BaseModel):
    id: UUID
    name: str
    start_date: str
    end_date: str
    learning_outcomes: Optional[List[str]] 
    status: StatusType
    last_accessed: str
    nCredit: int
    nSemester: int
    courseID: str
    image: str
    # percentage_complete: str
 
class GetCoursesPaginatedResponse(BaseModel):
    content: List[GetCoursesResponse]
    currentPage: int
    pageSize: int
    totalRows: int
    totalPages: int
class GetDocumentsResponse(BaseModel):
    id: UUID
    name: str
    type: DocumentType
    url: str
class GetExercisesResponse(BaseModel):
    id: UUID
    name: str
    description: str
    status: StatusType
    type: ExerciseType
class GetLessonsResponse(BaseModel):
    id: UUID
    title: str
    description: str 
    learning_outcomes: List[str]
    order: int
    # exercises: List[GetExercisesResponse]
    # documents: List[GetDocumentsResponse]
class GetCourseDetailResponse(BaseModel):
    course_id: str
    course_name: str
    course_start_date: str
    course_end_date: str
    course_learning_outcomes: List[str]
    course_status: str
    course_image: str
    course_percentage_complete: str
    course_last_accessed: str
    completed_lessons: int
    time_spent:str 
    assignments_done: int
    # lessons: List[GetLessonsResponse]
    
class BookmarkLessonResponse(BaseModel):
    lesson_id: UUID
    student_id: UUID
    course_id: UUID
    
class GetLessonsRecommendationResponse(BaseModel):
    course_id: UUID
    course_name: str
    lesson_id: UUID
    bookmark: bool
    status: StatusType
    title: str
    description: str
    order: int
class PutLearningOutcomesCoursesResponse(BaseModel):
    course_id: UUID
    learning_outcomes: list[str]