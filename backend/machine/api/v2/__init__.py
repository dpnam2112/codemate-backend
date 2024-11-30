from fastapi import APIRouter

from .courses import router as courses_router

router = APIRouter(prefix="/v2")

router.include_router(courses_router)

__all__ = ["router"]
