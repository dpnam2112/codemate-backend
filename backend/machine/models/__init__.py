from core.db import Base  # noqa: F401, This import is necessary for Alembic to detect the models

from .user import User  # noqa: F401
from .courses import Courses  
from .student_courses import StudentCourses  