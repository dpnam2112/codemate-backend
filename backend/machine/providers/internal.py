from functools import partial

from fastapi import Depends

import machine.controllers as ctrl
import machine.models as modl
import machine.repositories as repo
from core.db.session import DB_MANAGER, Dialect
from core.utils import singleton


@singleton
class InternalProvider:
    """
    This provider provides controllers related to internal services.
    """

    # DB Session Keeper
    db_session_keeper = DB_MANAGER[Dialect.POSTGRES]

    # Repositories
    user_repository = partial(repo.UserRepository, model=modl.User)
    
    # Ensure to pass the `model` argument explicitly to StudentCoursesRepository
    student_courses_repository = partial(repo.StudentCoursesRepository, model=modl.StudentCourses)

    def get_user_controller(self, db_session=Depends(db_session_keeper.get_session)):
        return ctrl.UserController(user_repository=self.user_repository(db_session=db_session))

    def get_dashboard_controller(self, db_session=Depends(db_session_keeper.get_session)):
        return ctrl.DashboardController(
            student_courses_repository=self.student_courses_repository(db_session=db_session)
        )
