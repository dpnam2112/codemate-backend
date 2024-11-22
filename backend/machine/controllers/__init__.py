from .user import UserController
from .dashboard import StudentCoursesController, ActivitiesController
from .courses import CoursesController, StudentLessonsController, StudentExercisesController
from .lessons import LessonsController
from .exercises import ExercisesController

__all__ = [
    "UserController",
    "StudentCoursesController",
    "ActivitiesController",
    "CoursesController",
    "LessonsController",
    "ExercisesController",
    "StudentLessonsController",
    "StudentExercisesController",
]
