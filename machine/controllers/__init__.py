from .user import StudentController, ProfessorController, AdminController, UserLoginsController
from .dashboard import StudentCoursesController, ActivitiesController
from .courses import CoursesController, StudentExercisesController
from .lessons import LessonsController, DocumentsController
from .exercises import ExercisesController
from .recommend import (
    ModulesController,
    RecommendDocumentsController,
    RecommendLessonsController,
    LearningPathsController,
    RecommendQuizzesController
)
from .feedback import FeedbackController
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
    "FeedbackController",
    "UserLoginsController"
]
