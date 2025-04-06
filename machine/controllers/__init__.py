from .user import StudentController, ProfessorController, AdminController, UserLoginsController
from .dashboard import StudentCoursesController, ActivitiesController
from .courses import CoursesController, StudentExercisesController
from .lessons import LessonsController, DocumentsController, ExtractedTextController
from .exercises import ExercisesController
from .recommend import (
    ModulesController,
    RecommendDocumentsController,
    RecommendLessonsController,
    LearningPathsController,
    RecommendQuizzesController,
    RecommendQuizQuestionController
)
from .feedback import FeedbackController
from .conversation import ConversationController
from .programming_language_config import ProgrammingLanguageConfigController

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
    "RecommendQuizQuestionController",
    "DocumentsController",
    "RecommendDocumentsController",
    "RecommendLessonsController",
    "LearningPathsController",
    "FeedbackController",
    "UserLoginsController",
    "ExtractedTextController",
    "ConversationController",
    "ProgrammingLanguageConfigController"
]
