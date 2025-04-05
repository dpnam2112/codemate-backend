from .user import StudentRepository, ProfessorRepository, AdminRepository, UserLoginsRepository
from .student_courses import StudentCoursesRepository
from .activities import ActivitiesRepository
from .courses import CoursesRepository
from .lessons import LessonsRepository
from .exercises import ExercisesRepository
from .student_exercises import StudentExercisesRepository
from .documents import DocumentsRepository, ExtractedTextRepository
from .modules import ModulesRepository
from .recommend_quizzes import RecommendQuizzesRepository,RecommendQuizQuestionRepository
from .recommend_documents import RecommendDocumentsRepository
from .learning_paths import LearningPathsRepository
from .recommend_lessons import RecommendLessonsRepository
from .feedback import FeedbackRepository
from .coding_assistant import ConversationRepository, MessageRepository

__all__ = [
    "StudentRepository",
    "ProfessorRepository",
    "AdminRepository",
    "StudentCoursesRepository",
    "ActivitiesRepository",
    "CoursesRepository",
    "LessonsRepository",
    "ExercisesRepository",
    "StudentLessonsRepository",
    "StudentExercisesRepository",
    "DocumentsRepository",
    "ModulesRepository",
    "RecommendDocumentsRepository",
    "LearningPathsRepository",
    "RecommendLessonsRepository",
    "RecommendQuizzesRepository",
    "RecommendQuizQuestionRepository",
    "FeedbackRepository",
    "UserLoginsRepository",
    "ExtractedTextRepository",
]
