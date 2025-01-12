from fastapi import APIRouter

from machine.api.v1.auth import router as auth_router
from machine.api.v1.user import router as user_router
from machine.api.v1.dashboard import router as dashboard_router
from machine.api.v1.courses import router as courses_router
from machine.api.v1.recommend import router as recommend_router
from machine.api.v1.module import router as module_quiz_router
from machine.api.v1.lesson import router as lesson_router
router = APIRouter(prefix="/v1")
router.include_router(auth_router)
router.include_router(user_router)
router.include_router(dashboard_router)
router.include_router(courses_router)
router.include_router(lesson_router)
router.include_router(recommend_router)
router.include_router(module_quiz_router)
__all__ = ["router"]
