#!main.py
import logging
import os
import uuid

import nest_asyncio
from fsspec.spec import AbstractFileSystem
from llama_index.vector_stores.postgres import PGVectorStore

from settings import PgVectorSettings, env_settings
from factories import get_embedding_instance, get_llm_instance
from services.fs_manager import FSManager
from services.document_ingestor import DocumentIngestor
from services.multimodal_query_engine import MultimodalQueryEngine
from logger import syslog

# Set up logging
logging.basicConfig(level=logging.DEBUG)
nest_asyncio.apply()


def main() -> None:
    """Main function to ingest a document using DocumentIngestor and execute multimodal queries.

    Steps:
      1. Initialize the file system, LLMs, and vector store.
      2. Upload a local PDF document to the abstract file system.
      3. Ingest the document into the vector store using DocumentIngestor.
      4. Query the vector store using a multimodal query engine.
    """
    # Initialize FSManager (e.g., S3 or local filesystem)
    fs_manager: FSManager = FSManager(protocol=env_settings.fsspec_protocol)

    # Initialize LLM instances for text and multimodal tasks.
    text_llm = get_llm_instance("gpt-4o-mini")
    multimodal_llm = get_llm_instance("gpt-4o")
    embed_model = get_embedding_instance()

    pgvector_settings = PgVectorSettings(pgvector_connection_string=env_settings.pgvector_connection_string)

    # Build the vector store instance (PGVectorStore).
    try:
        vector_store: PGVectorStore = PGVectorStore.from_params(
            host=env_settings.pgvector_host,
            port=str(env_settings.pgvector_port),
            table_name="multimodal_rag_test",
            schema_name="llamaindex_vectorstore",
            user=pgvector_settings.pgvector_username,
            password=pgvector_settings.pgvector_password,
            database=pgvector_settings.pgvector_database,
            embed_dim=1536,
        )
        # Initialize the vector store (if needed) with an empty index.
        vector_store.add([])
    except Exception as e:
        print(f"Error initializing vector store: {e}")
        return

    ingestor = DocumentIngestor(
        vector_store=vector_store,
        fs=fs_manager.fs,
        llamaparse_api_key=env_settings.llamaparse_api_key,
        text_llm=text_llm,
        multimodal_llm=multimodal_llm,
        embed_model=embed_model
    )

    image_node = ingestor.create_image_node(
        temp_image_path="./documents/transformer-architecture.png",
        context_str=""
    )

    syslog.debug(image_node)
    vector_store.add([image_node])

if __name__ == "__main__":
    main()


