from sqlalchemy.ext.asyncio import AsyncSession
from utils import singleton
from repositories import DocumentCollectionRepository
from db_models import DocumentCollection
from fastapi import Depends
from db_session import get_db_session

@singleton
class RepositoryProvider:
    def get_document_collection_repository(
        self, db_session: AsyncSession = Depends(get_db_session)
    ):
        return DocumentCollectionRepository(
                model=DocumentCollection,
                db_session=db_session
            )
