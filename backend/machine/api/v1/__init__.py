from fastapi import APIRouter

from machine.api.v1.auth import router as auth_router

router = APIRouter(prefix="/v1")
router.include_router(auth_router)

__all__ = ["router"]
