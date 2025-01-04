from functools import partial

from fastapi import Depends

import machine.controllers as ctrl
from machine.controllers.ai.recommender import AIRecommenderController
import machine.models as modl
import machine.repositories as repo
from core.db.session import DB_MANAGER, Dialect
from core.utils import singleton


@singleton
class InternalProvider:
    """
    This provider provides controllers related to internal services.
    """

    db_session_keeper = DB_MANAGER[Dialect.POSTGRES]

    user_repository = partial(repo.UserRepository, model=modl.User)
    
    student_courses_repository = partial(repo.StudentCoursesRepository, model=modl.StudentCourses)

    activities_repository = partial(repo.ActivitiesRepository, model=modl.Activities)
    
    courses_repository = partial(repo.CoursesRepository, model=modl.Courses)
    
    lessons_repository = partial(repo.LessonsRepository, model=modl.Lessons)
    
    exercises_repository = partial(repo.ExercisesRepository, model=modl.Exercises)
    
    student_lessons_repository = partial(repo.StudentLessonsRepository, model=modl.StudentLessons)
    
    student_exercises_repository = partial(repo.StudentExercisesRepository, model=modl.StudentExercises)
    
    documents_repository = partial(repo.DocumentsRepository, model=modl.Documents)

    modules_repository = partial(repo.ModulesRepository, model=modl.Modules)
    
    quiz_exercises_repository = partial(repo.QuizExercisesRepository, model=modl.QuizExercises)
    
    recommend_documents_repository = partial(repo.RecommendDocumentsRepository, model=modl.RecommendDocuments)
    
    recommend_lessons_repository = partial(repo.RecommendLessonsRepository, model=modl.RecommendLessons)
    
    learning_paths_repository = partial(repo.LearningPathsRepository, model=modl.LearningPaths)
    
    def get_user_controller(self, db_session=Depends(db_session_keeper.get_session)):
        return ctrl.UserController(user_repository=self.user_repository(db_session=db_session))

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
        
    def get_studentlessons_controller(self, db_session=Depends(db_session_keeper.get_session)):
        return ctrl.StudentLessonsController(
            student_lessons_repository=self.student_lessons_repository(db_session=db_session)
        )
        
    def get_studentexercises_controller(self, db_session=Depends(db_session_keeper.get_session)):
        return ctrl.StudentExercisesController(
            student_exercises_repository=self.student_exercises_repository(db_session=db_session)
        )
    
    def get_modules_controller(self, db_session=Depends(db_session_keeper.get_session)):
        return ctrl.ModulesController(
            modules_repository=self.modules_repository(db_session=db_session)
        )
    
    def get_quizexercises_controller(self, db_session=Depends(db_session_keeper.get_session)):
        return ctrl.QuizExercisesController(
            quiz_exercises_repository=self.quiz_exercises_repository(db_session=db_session)
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
            learning_paths_repository=self.learning_paths_repository(db_session=db_session)
        )

    def get_ai_recommender_controller(self, db_session=Depends(db_session_keeper.get_session)):
        """
        Provides an instance of AIRecommenderController.

        Args:
            db_session (AsyncSession): Database session dependency.

        Returns:
            AIRecommenderController: Controller for managing AI-based recommendations.
        """
        return AIRecommenderController(
            recommend_lesson_repository=self.recommend_lessons_repository(db_session=db_session),
            learning_paths_repository=self.learning_paths_repository(db_session=db_session),
        )
