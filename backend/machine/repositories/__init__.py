from .user import UserRepository
from .student_courses import StudentCoursesRepository
from .activities import ActivitiesRepository
from .courses import CoursesRepository
from .lessons import LessonsRepository
from .exercises import ExercisesRepository

__all__ = [
    "UserRepository",
    "StudentCoursesRepository",
    "ActivitiesRepository",
    "CoursesRepository",
    "LessonsRepository",
    "ExercisesRepository",
]
