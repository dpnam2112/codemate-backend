from fastapi import APIRouter
from .recommender import router as recommender_router

# Define the AI-specific router
router = APIRouter(prefix="/ai", tags=["AI"])
router.include_router(recommender_router)

__all__ = ["router"]
