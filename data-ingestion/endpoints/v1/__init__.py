from fastapi import APIRouter
from .document_collection import router as document_collection_router

router = APIRouter(prefix="/v1")

router.include_router(document_collection_router)

@router.get("/", tags=["V1"])
async def ping():
    return {"message": "API version 1"}
