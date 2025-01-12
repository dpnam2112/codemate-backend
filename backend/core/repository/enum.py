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
class QuestionType(Enum):
    multiple_choice = "multiple_choice"
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
     pdf =  "PDF"
     doc =  "DOC"
     docx =  "DOCX"
     ppt =  "PPT"
     pptx =  "PPTX"
     xls =  "XLS"
     xlsx =  "XLSX"
     txt =  "TXT"
     mp4 = "MP4"
     mp3 = "MP3"
     jpg =  "JPG"
     png =  "PNG"
