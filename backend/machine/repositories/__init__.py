from .user import UserRepository
from .student_courses import StudentCoursesRepository
from .activities import ActivitiesRepository
from .courses import CoursesRepository
from .lessons import LessonsRepository
from .exercises import ExercisesRepository
from .student_lessons import StudentLessonsRepository
from .student_exercises import StudentExercisesRepository
from .documents import DocumentsRepository
__all__ = [
    "UserRepository",
    "StudentCoursesRepository",
    "ActivitiesRepository",
    "CoursesRepository",
    "LessonsRepository",
    "ExercisesRepository",
    "StudentLessonsRepository",
    "StudentExercisesRepository",
    "DocumentsRepository",
]
