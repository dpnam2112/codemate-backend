from .user import StudentController, ProfessorController, AdminController
from .dashboard import StudentCoursesController, ActivitiesController
from .courses import CoursesController, StudentLessonsController, StudentExercisesController
from .lessons import LessonsController, DocumentsController
from .exercises import ExercisesController
from .recommend import ModulesController, QuizExercisesController, RecommendDocumentsController, RecommendLessonsController, LearningPathsController
__all__ = [
    "StudentController",
    "ProfessorController",
    "AdminController",
    "StudentCoursesController",
    "ActivitiesController",
    "CoursesController",
    "LessonsController",
    "ExercisesController",
    "StudentLessonsController",
    "StudentExercisesController",
    "ModulesController",
    "QuizExercisesController",
    "DocumentsController",
    "RecommendDocumentsController",
    "RecommendLessonsController",
    "LearningPathsController",
]
