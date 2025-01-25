from uuid import UUID
from pydantic import BaseModel
from typing import List, Optional
from datetime import date
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
class LessonInLearningPath(BaseModel):
    lesson_id: UUID
    lesson_name: str
    description: str
    progress: int
class LearningPathProgressInCourse(BaseModel):
    learning_path_id: UUID
    progress: int
    objective: Optional[str]
    lessons: List[LessonInLearningPath]
    
class ExeriseStudentProgressInCourse(BaseModel):
    exercise_id: UUID
    exercise_name: str
    score: int
class StudentProgressInCourse(BaseModel):
    student_id: UUID
    student_name: str
    exercises: List[ExeriseStudentProgressInCourse]
    learning_path: Optional[LearningPathProgressInCourse]
    average_score: float
    
class GetCourseGradesResponse(BaseModel):
    students_list: List[StudentProgressInCourse]
    
class AnswerQuizExercise(BaseModel):
    question: str
    answers: Optional[List[str]]
class StudentProgressInExercise(BaseModel):
    student_id: UUID
    student_name: str
    score: float
    date: Optional[date]
    question_answers: Optional[List[AnswerQuizExercise]]

class GetExerciseGradesResponse(BaseModel):
    students_list: List[StudentProgressInExercise]
    type: ExerciseType