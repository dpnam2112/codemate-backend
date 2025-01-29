from fastapi import APIRouter
from .lp_planner import router as lp_planner_router

# Define the AI-specific router
router = APIRouter(prefix="/ai", tags=["AI"])
router.include_router(lp_planner_router)

__all__ = ["router"]
