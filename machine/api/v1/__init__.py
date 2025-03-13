from fastapi import APIRouter

from machine.api.v1.auth import router as auth_router
from machine.api.v1.protected import router as protected_router
from machine.api.v1.user import router as user_router
from machine.api.v1.dashboard import router as dashboard_router
from machine.api.v1.courses import router as courses_router
from machine.api.v1.recommend import router as recommend_router
from machine.api.v1.module import router as module_quiz_router
from machine.api.v1.lesson import router as lesson_router
# from machine.api.v1.progress_tracking import router as progress_tracking_router
from machine.api.v1.exercise import router as exercise_router
from machine.api.v1.professor_progress_tracking import router as professor_progress_tracking
# from .ai.router import router as ai_router
from machine.api.v1.feedback import router as feedback_router
from machine.api.v1.professor import router as professor_router
from machine.api.v1.ai_routers import router as ai_router
router = APIRouter(prefix="/v1")
router.include_router(auth_router)
router.include_router(user_router)
router.include_router(protected_router)
router.include_router(dashboard_router)
router.include_router(courses_router)
router.include_router(lesson_router)
router.include_router(exercise_router)
router.include_router(recommend_router)
router.include_router(professor_router)
router.include_router(professor_progress_tracking)
router.include_router(module_quiz_router)
# router.include_router(progress_tracking_router)
# router.include_router(ai_router)
router.include_router(feedback_router)
router.include_router(ai_router)

__all__ = ["router"]
