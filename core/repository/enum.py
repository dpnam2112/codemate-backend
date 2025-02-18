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
    add_feedback = "add_feedback"


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
    quiz = "quiz"
    code = "code"

class GradingMethodType(Enum):
    highest = "highest"
    average = "average"
    latest = "latest"
    first = "first"
class LessonType(Enum):
    original = "original"
    recommended = "recommended"


class DifficultyLevel(Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class QuestionType(Enum):
    multiple_choice = "multiple_choice"
    single_choice = "single_choice"
    true_false = "true_false"
    fill_in_the_blank = "fill_in_the_blank"
    short_answer = "short_answer"
    long_answer = "long_answer"
    matching = "matching"
    ordering = "ordering"
    essay = "essay"
    problem_solving = "problem_solving"
    project = "project"
    presentation = "presentation"
    report = "report"
    case_study = "case_study"
    other = "other"


class DocumentType(Enum):
    csv = "CSV"
    pdf = "PDF"
    doc = "DOC"
    docx = "DOCX"
    ppt = "PPT"
    pptx = "PPTX"
    xls = "XLS"
    xlsx = "XLSX"
    txt = "TXT"
    mp4 = "MP4"
    mp3 = "MP3"
    jpg = "JPG"
    png = "PNG"


class FeedbackCategory(Enum):
    user_interface = "user_interface"
    performance = "performance"
    feature_request = "feature_request"
    bug_report = "bug_report"
    other = "other" 


class FeedbackType(Enum):
    system = "system"
    course = "course"
    
class FeedbackStatusType(Enum):
    pending = "pending"
    in_progress = "in_progress"
    resolved = "resolved"
