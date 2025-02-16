import uuid
from repositories import DocumentCollectionRepository
from settings import PgVectorSettings


class DocumentCollectionService:
    def __init__(
        self,
        pgvector_settings: PgVectorSettings,
        document_collection_repo: DocumentCollectionRepository
    ):
        self.pgvector_settings = pgvector_settings
        self.document_collection_repo = document_collection_repo

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
        self._init_llamaindex_vector_store(
            collection_name=name,
            collection_id=collection_id
        )

        return document_collection

    def _init_llamaindex_vector_store(self, collection_name: str, collection_id: str):
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
            table_name=f"{collection_name}_{collection_id}",
            schema_name="llamaindex_vectorstore",
            user=self.pgvector_settings.username,
            password=self.pgvector_settings.password,
            database=self.pgvector_settings.database,
            embed_dim=1536
        )
        
        # Initalize the vector store without persisting any nodes.
        vector_store.add([])
        return vector_store
    
    def ingest_documents_to_collection(
        self, collection_id: uuid.UUID, s3_key: str
    ):
        pass
