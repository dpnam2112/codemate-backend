from enum import Enum

class SynchronizeSessionEnum(Enum):
    FETCH = "fetch"
    EVALUATE = "evaluate"
    FALSE = False
    
    from enum import Enum

class ActivityType(str, Enum):
    VIEW_COURSE = "view_course"
    RESUME_ACTIVITY = "resume_activity"
    COMPLETE_LESSON = "complete_lesson"
    COMPLETE_ASSIGNMENT = "complete_assignment"
    ENROLL_COURSE = "enroll_course"
    BADGE_EARNED = "badge_earned"

class StatusType(str, Enum):
    new = "New"
    in_progress = "In Progress"
    completed = "Completed"


class UserRole(Enum):
    student = "student"
    professor = "professor"
    admin = "admin"


class LessonType(Enum):
    original = "original"  
    recommended = "recommended"
