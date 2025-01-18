from uuid import UUID
from pydantic import BaseModel
from typing import List
from core.repository.enum import *

# class CourseProgressTrackingResponse:
#     course_id: UUID
#     course_name: str
#     course_start_date: str
#     course_end_date: str
#     course_learning_outcomes: List[str]
#     percentage_complete: str
#     last_accessed: str
class CourseNameResponse(BaseModel):
    course_id: UUID
    course_name: str
class GetCoursesListResponse(BaseModel):
    course_name_list: List[CourseNameResponse]
class ExerciseNameResponse(BaseModel):
    exercise_id: UUID
    exercise_name: str
class GetExercisesListResponse(BaseModel):
    exercises_name_list: List[ExerciseNameResponse]