import uuid

from fastapi import File, UploadFile
from fsspec import AbstractFileSystem
from repositories import DocumentCollectionRepository
from settings import PgVectorSettings
from db_models import Document


class DocumentCollectionService:
    def __init__(
        self,
        pgvector_settings: PgVectorSettings,
        document_collection_repo: DocumentCollectionRepository,
        fs: AbstractFileSystem # currently this is s3 filesystem
    ):
        self.pgvector_settings = pgvector_settings
        self.document_collection_repo = document_collection_repo
        self.fs = fs

    def create_document_collection(
        self, name: str, description: str
    ):
        """
        Create a new document collection.
        """
        collection_id = str(uuid.uuid4())

        # TODO: Create a new ORM model instance to represent the document collection.
        document_collection = self.document_collection_repo.create(
                attributes={
                    "id": uuid.uuid4(),
                    "name": name,
                    "description": description,
                },
                commit=True
        )

        # Create a new vector store for the collection.
        self._get_or_create_llamaindex_vector_store(
            collection_id=collection_id
        )

        return document_collection

    async def ingest_documents(self, collection_id: str, file_urls: list[str]):
        # TODO: Download and store the document, then ingest the document to the vector database.
        # This method should be implemented in a way so that it can be processed concurrently.
        pass


    def _store_document(self, file_url: str) -> Document:
        # Conceptually store a document to the document collection
        # TODO: Download the file, create a Document instance to represent the document file
        # internally, then put the file to the file system (in this case, s3)
        pass

    def _ingest(self, file_key: str):
        # Ingest the file to the vector store.
        # Based on the example in `main.py` to implement this method.
        # TODO
        pass

    def _get_or_create_llamaindex_vector_store(self, collection_id: str):
        """
        Initialize an empty LlamaIndex vector store without persisting any nodes.
        """
        # Import the PGVectorStore from LlamaIndex.
        from llama_index.vector_stores.postgres import PGVectorStore

        # Initialize the PGVectorStore.
        # Here we pass in the connection URIs and set an embedding dimension.
        vector_store = PGVectorStore.from_params(
            host=self.pgvector_settings.pgvector_host,
            port=str(self.pgvector_settings.pgvector_port),
            table_name=f"document_collection_{collection_id}",
            schema_name="llamaindex_vectorstore",
            user=self.pgvector_settings.pgvector_username,
            password=self.pgvector_settings.pgvector_password,
            database=self.pgvector_settings.pgvector_database,
            embed_dim=1536
        )
        
        # Initalize the vector store without persisting any nodes.
        vector_store.add([])
        return vector_store
    
    def ingest_documents_to_collection(
        self, collection_id: uuid.UUID, file_key: str
    ):
        pass
