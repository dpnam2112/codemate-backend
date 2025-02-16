from fastapi import Depends
from repositories.collection import DocumentCollectionRepository
from services.document_collection import DocumentCollectionService
from utils import singleton
from settings import PgVectorSettings, env_settings
from .repositories import RepositoryProvider

@singleton
class ServiceProvider:
    def get_document_collection_service(
        self,
        document_collection_repo: DocumentCollectionRepository = Depends(RepositoryProvider().get_document_collection_repository)
    ):
        pgvector_settings = PgVectorSettings(
                    pgvector_connection_string=env_settings.pgvector_connection_string
                )

        return DocumentCollectionService(
                pgvector_settings=pgvector_settings,
                document_collection_repo=document_collection_repo
        )
