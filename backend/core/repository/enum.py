from enum import Enum

class SynchronizeSessionEnum(Enum):
    FETCH = "fetch"
    EVALUATE = "evaluate"
    FALSE = False
    
    from enum import Enum

class ActivityType(str, Enum):
    view_course = "view_course"
    resume_activity = "resume_activity"
    complete_lesson = "complete_lesson"
    complete_assignment = "complete_assignment"
    enroll_course = "enroll_course"
    badge_earned = "badge_earned"

class StatusType(str, Enum):
    new = "new"
    in_progress = "in Progress"
    completed = "completed"


class UserRole(Enum):
    student = "student"
    professor = "professor"
    admin = "admin"

class ExerciseType(Enum):
    original = "original"
    recommended = "recommended"

class LessonType(Enum):
    original = "original"  
    recommended = "recommended"

class DifficultyLevel(Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"