from fastapi import APIRouter
from endpoints.v1 import router as router_v1

router = APIRouter(prefix="")

@router.get("/ping", tags=["Health"])
async def ping():
    """
    A simple health check endpoint that returns a pong response.
    """
    return {"message": "pong"}

router.include_router(router_v1)
