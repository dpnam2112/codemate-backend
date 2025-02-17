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
    try:
        text_llm = get_llm_instance("gpt-4o-mini")
        multimodal_llm = get_llm_instance("gpt-4o")
        embed_model = get_embedding_instance()
    except Exception as e:
        print(f"Error initializing LLMs: {e}")
        return

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

    # Upload the local PDF to the abstract file system.
    local_pdf_path: str = env_settings.pdf_path
    with open(local_pdf_path, "rb") as f:
        file_content: bytes = f.read()
    file_key: str = f"documents/{uuid.uuid4()}.pdf"
    with fs_manager.fs.open(file_key, "wb+") as remote_file:
        remote_file.write(file_content)
    print(f"Uploaded document to: {file_key}")

    # Create an instance of DocumentIngestor.
    ingestor = DocumentIngestor(
        vector_store=vector_store,
        fs=fs_manager.fs,
        llamaparse_api_key=env_settings.llamaparse_api_key,
        text_llm=text_llm,
        multimodal_llm=multimodal_llm,
        embed_model=embed_model
    )

    # Ingest the document.
    index = ingestor.ingest(file_key)
    syslog.info(f"Document ingested successfully from: {file_key}")

    # Create a multimodal query engine and run a sample query.
    try:
        query_engine_instance = MultimodalQueryEngine(
            retriever=index.as_retriever(similarity_top_k=3),
            multi_modal_llm=multimodal_llm,
        )
        query: str = "Summary the transformer"
        response = query_engine_instance.custom_query(query)
        print(f"Response with contextual retrieval:\n{response}\n")
    except Exception as e:
        print(f"Error during query execution: {e}")
        return


if __name__ == "__main__":
    main()

