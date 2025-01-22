from .user import StudentController, ProfessorController, AdminController
from .dashboard import StudentCoursesController, ActivitiesController
from .courses import CoursesController, StudentExercisesController
from .lessons import LessonsController, DocumentsController
from .exercises import ExercisesController
from .recommend import (
    ModulesController,
    QuizExercisesController,
    RecommendDocumentsController,
    RecommendLessonsController,
    LearningPathsController,
)

from .recommend import ModulesController, RecommendQuizzesController, RecommendDocumentsController, RecommendLessonsController, LearningPathsController
__all__ = [
    "StudentController",
    "ProfessorController",
    "AdminController",
    "StudentCoursesController",
    "ActivitiesController",
    "CoursesController",
    "LessonsController",
    "ExercisesController",
    "StudentExercisesController",
    "ModulesController",
    "RecommendQuizzesController",
    "DocumentsController",
    "RecommendDocumentsController",
    "RecommendLessonsController",
    "LearningPathsController",
]
