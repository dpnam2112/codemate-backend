from functools import partial

from fastapi import Depends
from openai import AsyncOpenAI, OpenAI

import machine.controllers as ctrl
from machine.controllers.ai.lp_planning import LPPPlanningController
import machine.models as modl
from core.utils import singleton
import machine.repositories as repo
from core.db.session import DB_MANAGER, Dialect
from core.settings import settings as env_settings
from machine.repositories.programming_tc import ProgrammingTestCaseRepository
import machine.services as services


@singleton
class InternalProvider:
    """
    This provider provides controllers related to internal services.
    """

    db_session_keeper = DB_MANAGER[Dialect.POSTGRES]

    student_repository = partial(repo.StudentRepository, model=modl.Student)
    
    professor_repository = partial(repo.ProfessorRepository, model=modl.Professor)
    
    admin_repository = partial(repo.AdminRepository, model=modl.Admin)
    
    student_courses_repository = partial(repo.StudentCoursesRepository, model=modl.StudentCourses)

    activities_repository = partial(repo.ActivitiesRepository, model=modl.Activities)
    
    courses_repository = partial(repo.CoursesRepository, model=modl.Courses)
    
    lessons_repository = partial(repo.LessonsRepository, model=modl.Lessons)
    
    exercises_repository = partial(repo.ExercisesRepository, model=modl.Exercises)
    
    student_exercises_repository = partial(repo.StudentExercisesRepository, model=modl.StudentExercises)
    
    documents_repository = partial(repo.DocumentsRepository, model=modl.Documents)

    modules_repository = partial(repo.ModulesRepository, model=modl.Modules)
    
    recommend_quizzes_repository = partial(repo.RecommendQuizzesRepository, model=modl.RecommendQuizzes)
    
    recommend_quiz_question_repository = partial(repo.RecommendQuizQuestionRepository, model=modl.RecommendQuizQuestion)
    
    recommend_documents_repository = partial(repo.RecommendDocumentsRepository, model=modl.RecommendDocuments)
    
    recommend_lessons_repository = partial(repo.RecommendLessonsRepository, model=modl.RecommendLessons)
    
    learning_paths_repository = partial(repo.LearningPathsRepository, model=modl.LearningPaths)
    
    feedback_repository = partial(repo.FeedbackRepository, model=modl.Feedback)
    
    user_logins_repository = partial(repo.UserLoginsRepository, model=modl.UserLogins)
    
    extracted_text_repository = partial(repo.ExtractedTextRepository, model=modl.ExtractedText)

    conversation_repository = partial(repo.ConversationRepository, model=modl.Conversation)

    message_repository = partial(repo.MessageRepository, model=modl.Message)

    pg_config_repo = partial(repo.ProgrammingLanguageConfigRepository, model=modl.ProgrammingLanguageConfig)

    programming_tc_repo = partial(ProgrammingTestCaseRepository)

    programming_submission_repo = partial(repo.ProgrammingSubmissionRepository, model=modl.ProgrammingSubmission)
    
    def get_student_controller(self, db_session=Depends(db_session_keeper.get_session)):
        return ctrl.StudentController(
            student_repository=self.student_repository(db_session=db_session)
        )
        
    def get_professor_controller(self, db_session=Depends(db_session_keeper.get_session)):
        return ctrl.ProfessorController(
            professor_repository=self.professor_repository(db_session=db_session)
        )
        
    def get_admin_controller(self, db_session=Depends(db_session_keeper.get_session)):
        return ctrl.AdminController(
            admin_repository=self.admin_repository(db_session=db_session)
        )

    def get_studentcourses_controller(self, db_session=Depends(db_session_keeper.get_session)):
        return ctrl.StudentCoursesController(
            student_courses_repository=self.student_courses_repository(db_session=db_session)
        )
    
    def get_activities_controller(self, db_session=Depends(db_session_keeper.get_session)): return ctrl.ActivitiesController(
            activities_repository=self.activities_repository(db_session=db_session)
        )

    def get_courses_controller(self, db_session=Depends(db_session_keeper.get_session)):
        return ctrl.CoursesController(
            courses_repository=self.courses_repository(db_session=db_session)
        )
        
    def get_lessons_controller(self, db_session=Depends(db_session_keeper.get_session)):
        return ctrl.LessonsController(
            lessons_repository=self.lessons_repository(db_session=db_session)
        )
        
    def get_exercises_controller(self, db_session=Depends(db_session_keeper.get_session)):
        # Use Google Gemini
        llm_aclient = AsyncOpenAI(
            api_key=env_settings.GEMINI_API_KEY,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )

        return ctrl.ExercisesController(
            exercises_repository=self.exercises_repository(db_session=db_session),
            submission_repo=self.programming_submission_repo(db_session=db_session),
            llm_client=llm_aclient
        )
        
    def get_studentexercises_controller(self, db_session=Depends(db_session_keeper.get_session)):
        return ctrl.StudentExercisesController(
            student_exercises_repository=self.student_exercises_repository(db_session=db_session)
        )
    
    def get_modules_controller(self, db_session=Depends(db_session_keeper.get_session)):
        return ctrl.ModulesController(
            modules_repository=self.modules_repository(db_session=db_session)
        )
    
    def get_recommend_quizzes_controller(self, db_session=Depends(db_session_keeper.get_session)):
        return ctrl.RecommendQuizzesController(
            recommend_quizzes_repository=self.recommend_quizzes_repository(db_session=db_session)
        )
    
    def get_recommend_quiz_question_controller(self, db_session=Depends(db_session_keeper.get_session)):
        return ctrl.RecommendQuizQuestionController(
            recommend_quiz_question_repository=self.recommend_quiz_question_repository(db_session=db_session)
        )
        
    def get_documents_controller(self, db_session=Depends(db_session_keeper.get_session)):
        return ctrl.DocumentsController(
            documents_repository=self.documents_repository(db_session=db_session)
        )
    
    def get_recommenddocuments_controller(self, db_session=Depends(db_session_keeper.get_session)):
        return ctrl.RecommendDocumentsController(
            recommend_documents_repository=self.recommend_documents_repository(db_session=db_session)
        )
    
    def get_recommendlessons_controller(self, db_session=Depends(db_session_keeper.get_session)):
        return ctrl.RecommendLessonsController(
            recommend_lessons_repository=self.recommend_lessons_repository(db_session=db_session)
        )
    
    def get_learningpaths_controller(self, db_session=Depends(db_session_keeper.get_session)):
        return ctrl.LearningPathsController(
            learning_paths_repository=self.learning_paths_repository(db_session=db_session),
            recommended_lesson_repository=self.recommend_lessons_repository(db_session=db_session)
        )
        
    def get_feedback_controller(self, db_session=Depends(db_session_keeper.get_session)):
        return ctrl.FeedbackController(
            feedback_repository=self.feedback_repository(db_session=db_session)
        )

    async def get_lp_planning_controller(self, db_session=Depends(db_session_keeper.get_session)):
        async with LPPPlanningController(
            recommend_lesson_repository=self.recommend_lessons_repository(db_session=db_session),
            learning_paths_repository=self.learning_paths_repository(db_session=db_session),
            module_repository=self.modules_repository(db_session=db_session)
        ) as controller:
            if controller is None:
                raise ValueError("Controller is not properly initialized.")
            yield controller
    
    def get_user_logins_controller(self, db_session=Depends(db_session_keeper.get_session)):
        return ctrl.UserLoginsController(
            user_logins_repository=self.user_logins_repository(db_session=db_session)
        )


    def get_extracted_text_controller(self, db_session=Depends(db_session_keeper.get_session)):
        return ctrl.ExtractedTextController(
            extracted_text_repository=self.extracted_text_repository(db_session=db_session)
        )

    def get_conversation_controller(self, db_session=Depends(db_session_keeper.get_session)) -> ctrl.ConversationController:
        return ctrl.ConversationController(
            model_class=modl.Conversation, repository=self.conversation_repository(db_session=db_session)
        )

    def get_pg_config_controller(self, db_session=Depends(db_session_keeper.get_session)) -> ctrl.ProgrammingLanguageConfigController:
        return ctrl.ProgrammingLanguageConfigController(
            model_class=modl.ProgrammingLanguageConfig, repository=self.pg_config_repo(db_session=db_session)
        )

    def get_programming_tc_controller(self, db_session=Depends(db_session_keeper.get_session)):
        return ctrl.ProgrammingTestCaseController(
            repository=self.programming_tc_repo(db_session=db_session)
        )

    def get_programming_submission_controller(self, db_session=Depends(db_session_keeper.get_session)):
        return ctrl.ProgrammingSubmissionController(
            model_class=modl.ProgrammingSubmission,
            repository=self.programming_submission_repo(db_session=db_session)
        )

    def get_learning_material_gen_controller(
        self, db_session=Depends(db_session_keeper.get_session)
    ) -> ctrl.LearningMaterialGenController:
        programming_exercise_service = services.ProgrammingExerciseGenService()

        return ctrl.LearningMaterialGenController(
            module_repo=self.modules_repository(db_session=db_session),
            exercises_repo=self.exercises_repository(db_session=db_session),
            pl_config_repo=self.pg_config_repo(db_session=db_session),
            testcase_repo=self.programming_tc_repo(db_session=db_session),
            programming_exercise_service=programming_exercise_service
        )
