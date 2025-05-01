from uuid import UUID
from pydantic import BaseModel
from typing import List, Optional
from core.repository.enum import *
from datetime import date
class StudentList(BaseModel):
    student_id: UUID
    student_name: str
    student_email: str
    student_avatar: str
    student_mssv: Optional[str]

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
    image_url: str
    nSemester: int
    nCredit: int
    courseID: str
    class_name: str
    learning_outcomes: Optional[List[str]] 
    status: StatusType
    last_accessed: str
    percentage_complete: str

 
class GetCoursesPaginatedResponse(BaseModel):
    content: List[GetCoursesResponse]
    currentPage: int
    pageSize: int
    totalRows: int
    totalPages: int
    
class GetAdminCoursesResponse(BaseModel):
    id: UUID
    name: str
    start_date: str
    end_date: str
    status: StatusType
    nCredit: int
    nSemester: int
    courseID: str
    class_name: str
    
class GetAdminCoursesPaginatedResponse(BaseModel):
    content: List[GetAdminCoursesResponse]
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
    course_nCredit: int
    course_nSemester: int
    course_courseID: str
    course_classname: str
    course_percentage_complete: str
    course_last_accessed: str
    completed_lessons: int
    time_spent:str 
    percentage_done: int
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
class GetDocumentsProfessor(BaseModel):
    id: UUID
    name: str
    type: str
    url: str
class GetExercisesProfessor(BaseModel):
    id: UUID
    name: str
    description: str
    type: ExerciseType
class GetLessonProfessor(BaseModel):
    id: UUID
    title: str
    description: str 
    order: int
    documents: List[GetDocumentsProfessor]
class GetProfessorCoursesResponse(BaseModel):
    id: UUID
    name: str
    start_date: date
    end_date: date
    student_list: List[StudentList]
    learning_outcomes: List[str]
    professor: ProfessorInformation
    status: StatusType
    image_url: str
    nSemester: int
    nCredit: int
    courseID: str
    class_name: str
class GetProfessorCoursesPaginatedResponse(BaseModel):
    content: List[GetProfessorCoursesResponse]
    currentPage: int
    pageSize: int
    totalRows: int
    totalPages: int
# class GetCourseDetailProfessorResponse(BaseModel):
#     course_id: UUID
#     course_name: str
#     course_start_date: str
#     course_end_date: str
#     course_learning_outcomes: List[str]
#     course_professor: ProfessorInformation
#     course_status: StatusType
#     course_image: str
#     exercises: List[GetExercisesProfessor]
#     students: List[StudentList]
#     lessons: List[GetLessonProfessor]  

class GetCourseDetailProfessorResponse(BaseModel):
    course_id: UUID
    course_name: str
    course_start_date: str
    course_end_date: str
    course_learning_outcomes: List[str]
    course_status: StatusType
    course_image_url: str
    course_nCredit: int
    course_nSemester: int
    course_courseID: str
    course_class_name: str
    nStudents: int
    nLessons: int
    nExercises: int
    nDocuments: int
    
