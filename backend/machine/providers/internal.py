from functools import partial

from fastapi import Depends

import machine.controllers as ctrl
from machine.controllers.ai.lp_planning import LPPPlanningController
import machine.models as modl
from core.utils import singleton
import machine.controllers as ctrl
import machine.repositories as repo
from core.db.session import DB_MANAGER, Dialect


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
    
    recommend_documents_repository = partial(repo.RecommendDocumentsRepository, model=modl.RecommendDocuments)
    
    recommend_lessons_repository = partial(repo.RecommendLessonsRepository, model=modl.RecommendLessons)
    
    learning_paths_repository = partial(repo.LearningPathsRepository, model=modl.LearningPaths)
    
    feedback_repository = partial(repo.FeedbackRepository, model=modl.Feedback)
    
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
    
    def get_activities_controller(self, db_session=Depends(db_session_keeper.get_session)):
        return ctrl.ActivitiesController(
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
        return ctrl.ExercisesController(
            exercises_repository=self.exercises_repository(db_session=db_session)
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
