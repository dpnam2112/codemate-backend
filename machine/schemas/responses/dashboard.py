from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
from core.repository.enum import ActivityType,ExerciseType
from typing import List, Optional, Union
class WelcomeMessageResponse(BaseModel):
    course: str
    course_id: UUID
    last_accessed: datetime
    
class GetRecentActivitiesResponse(BaseModel):
    activity_id: UUID
    activity_description: str
    activity_type: str
    activity_date: datetime
    
class Events(BaseModel):
    exercise_id: UUID
    exercise_name: str
    exercise_time_open: Union[str, datetime]
    exercise_time_close: Union[str, datetime]
    exercise_type: ExerciseType
    course_name: str
    course_id: UUID
    course_courseID: str
    course_nSemester: int
    
class GetDashboardProfessorResponse(BaseModel):
    professor_id: UUID
    professor_name: str
    nCourses: int
    nLessons: int
    nStudents: int
    nExercises: int
    upcoming_events: Optional[List[Events]]
    
    
class StudentActivityResponse(BaseModel):
    activity_id: UUID
    student_id: UUID
    student_name: str
    activity_type: str
    activity_description: str
    activity_timestamp: str
    course_id: Optional[UUID]
    course_name: Optional[str]