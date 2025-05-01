from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import date

class BookmarkLessonRequest(BaseModel):
    student_id: UUID
    lesson_id: UUID
    course_id: UUID
    
class CreateCourseRequest(BaseModel):
      id: Optional[int]
      name: str
      professorID: str
      creditNumber: int
      studentIDs: List[str]
      nSemester: int
      courseID: str
      startDate: date
      endDate: date
      class_name: str
    
class StudentCoursesListResponse(BaseModel):
    student_id: UUID
    course_id: UUID
    last_accessed: str
    completed_lessons: int
    time_spent: str
    percentage_done: int
class CreateCourseResponse(BaseModel):
    course_id: UUID
    courseID: str
    name: str
    professor_id: UUID
    start_date: str
    end_date: str
    status: str
    nCredit: int
    nSemester: int
    learning_outcomes: str
    image_url: str
    student_courses_list: List[StudentCoursesListResponse]
    
class PutLearningOutcomesCoursesRequest(BaseModel):
    learning_outcomes: List[str]

class UpdateCourseRequest(BaseModel):
    name: Optional[str] = None
    professor_id: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None
    n_credit: Optional[int] = None
    n_semester: Optional[int] = None
    courseID: Optional[str] = None
    class_name: Optional[str] = None
    
    
class AddStudentsToCourseRequest(BaseModel):
    """
    Request model for adding students to an existing course
    """
    course_id: str = Field(..., description="The ID of the course to add students to")
    student_ids: List[str] = Field(..., min_items=1, description="List of student MSVVs to add to the course")

class StudentCourseInfo(BaseModel):
    """
    Information about a student's enrollment in a course
    """
    student_id: str
    student_mssv: Optional[str] = None
    course_id: str
    last_accessed: Optional[str] = None
    completed_lessons: Optional[int] = None
    time_spent: Optional[str] = None
    percentage_done: Optional[int] = None
    
    class Config:
        # Allow extra fields during validation
        extra = "ignore"

class AddStudentsToCourseResponse(BaseModel):
    """
    Response model for the add students to course endpoint
    """
    course_id: str
    course_name: str
    added_students_count: int
    already_enrolled_count: int
    student_courses_list: List[StudentCourseInfo]