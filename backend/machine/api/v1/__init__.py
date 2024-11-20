from fastapi import APIRouter

from machine.api.v1.auth import router as auth_router
from machine.api.v1.user import router as user_router
from machine.api.v1.dashboard import router as dashboard_router
from machine.api.v1.courses import router as courses_router

router = APIRouter(prefix="/v1")
router.include_router(auth_router)
router.include_router(user_router)
router.include_router(dashboard_router)
router.include_router(courses_router)

__all__ = ["router"]
