from fastapi import APIRouter

router = APIRouter(prefix="/v1")

@router.get("/", tags=["V1"])
async def ping():
    return {"message": "API version 1"}
