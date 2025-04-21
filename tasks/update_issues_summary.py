from uuid import UUID
from dramatiq import actor
from sqlalchemy import select
from core.db.session import DB_MANAGER, Dialect
from core.db.utils import session_context
from core.llm.model_config import LLMModelConfig
from machine.models.coding_submission import ProgrammingSubmission
from machine.models.student_courses import StudentCourses, LearningIssue, IssuesSummary
from machine.models.exercises import Exercises
from machine.models.courses import Courses
from core.logger import syslog
from worker import broker
from datetime import datetime
from machine.services.code_exercise_assistant import CodeExerciseAssistantService
from core.settings import settings as env_settings

async def resolve_course_and_student_course(session, exercise: Exercises, user_id: UUID) -> tuple[Courses | None, StudentCourses | None]:
    """
    Resolves the associated course for an exercise, either directly or via module_id path.
    """
    if exercise.course_id:
        stmt = (
            select(Courses, StudentCourses)
            .outerjoin(
                StudentCourses,
                (StudentCourses.student_id == user_id) & (StudentCourses.course_id == Courses.id)
            )
            .where(Courses.id == exercise.course_id)
        )
        result = await session.execute(stmt)
        return result.first()

    if exercise.module_id:
        from machine.models.modules import Modules
        from machine.models.recommend_lessons import RecommendLessons
        from machine.models.learning_paths import LearningPaths

        stmt = (
            select(Courses, StudentCourses)
            .join(LearningPaths, LearningPaths.course_id == Courses.id)
            .join(RecommendLessons, RecommendLessons.learning_path_id == LearningPaths.id)
            .join(Modules, Modules.recommend_lesson_id == RecommendLessons.id)
            .filter(Modules.id == exercise.module_id)
            .outerjoin(
                StudentCourses,
                (StudentCourses.student_id == user_id) & (StudentCourses.course_id == Courses.id)
            )
        )
        result = await session.execute(stmt)
        return result.first()

    return None, None

@actor(max_retries=3, min_backoff=10, max_backoff=60, broker=broker)
async def update_issues_summary_task(submission_id_str: str):
    submission_id = UUID(submission_id_str)
    async with session_context(DB_MANAGER[Dialect.POSTGRES]) as session:
        # Fetch all required data in a single query
        stmt = select(
            ProgrammingSubmission,
            Exercises,
        ).join(
            Exercises, ProgrammingSubmission.exercise_id == Exercises.id
        ).where(
            ProgrammingSubmission.id == submission_id
        )

        result = await session.execute(stmt)
        row = result.first()

        if not row:
            syslog.error(f"Submission {submission_id} not found or exercise missing")
            return

        submission, exercise = row
        course, student_course = await resolve_course_and_student_course(session, exercise, submission.user_id)

        if not course:
            syslog.error(f"Could not resolve course for exercise {exercise.id}")
            return

        # Create student course record if it doesn't exist
        if not student_course:
            student_course = StudentCourses(
                student_id=submission.user_id,
                course_id=course.id
            )
            session.add(student_course)
            await session.flush()
            syslog.info(f"Created new student course record for student {submission.user_id}")

        # Get current issues summary
        current_summary = student_course.issues_summary or {"common_issues": []}
        issues_summary = IssuesSummary.model_validate_json(current_summary)

        # Get LLM analysis
        llm_cfg = LLMModelConfig(
            model_name="gemini/gemini-2.0-flash",
            api_key=env_settings.GEMINI_API_KEY
        )
        assistant_service = CodeExerciseAssistantService(llm_cfg)
        analysis = await assistant_service.analyze_learning_issues(
            code=submission.code,
            course_title=course.name,
            course_objectives=course.learning_outcomes,
            exercise_title=exercise.name,
            exercise_description=exercise.description,
            current_issues=[issue.model_dump(mode="json") for issue in issues_summary.common_issues]
        )

        if not analysis:
            syslog.error(f"Failed to analyze learning issues for submission {submission_id}")
            return

        # If LLM found no issues, clear the issues list
        if not analysis.issues:
            pass
        else:
            existing_issues = {issue.type: issue for issue in issues_summary.common_issues}
            
            # Process new issues
            for issue in analysis.issues:
                if issue.type in existing_issues:
                    # Update existing issue
                    existing_issues[issue.type].frequency += 1
                    existing_issues[issue.type].last_occurrence = datetime.now()
                    syslog.info(f"Incremented frequency for issue type {issue.type}")
                else:
                    # Add new issue
                    new_issue = LearningIssue(
                        type=issue.type,
                        description=issue.description,
                        frequency=1,
                        related_lessons=[str(exercise.id)],
                        last_occurrence=datetime.now()
                    )
                    issues_summary.common_issues.append(new_issue)
                    existing_issues[issue.type] = new_issue
                    syslog.info(f"Added new issue type {issue.type}")

        student_course.issues_summary = issues_summary.model_dump_json()
        await session.commit()
        syslog.info(f"Updated issues summary for student {submission.user_id} in course {course.id}")
