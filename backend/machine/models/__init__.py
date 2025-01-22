from core.db import Base  # noqa: F401, This import is necessary for Alembic to detect the models

from .student import Student
from .professor import Professor 
from .admin import Admin
from .courses import Courses  
from .student_courses import StudentCourses  
from .activities import Activities
from .lessons import Lessons
from .exercises import Exercises
from .student_exercises import StudentExercises
from .documents import Documents
from .modules import Modules
from .recommend_quizzes import RecommendQuizzes
from .recommend_documents import RecommendDocuments
from .recommend_lessons import RecommendLessons
from .learning_paths import LearningPaths