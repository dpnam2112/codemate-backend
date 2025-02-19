#!cli.py
import argparse
import asyncio
import uuid
import nest_asyncio
from pathlib import Path
from typing import Any

from llama_index.vector_stores.postgres import PGVectorStore
from logger import syslog
from factories import get_embedding_instance, get_llm_instance
from services.document_ingestor import DocumentIngestor
from settings import PgVectorSettings, env_settings
from fsspec.implementations.local import LocalFileSystem


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the ingestion CLI.

    Returns:
        argparse.Namespace: Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Multimodal RAG Pipeline Ingestion CLI"
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        required=True,
        help="Path to the local PDF file to be ingested.",
    )
    parser.add_argument(
        "--document-bucket",
        type=str,
        default=getattr(env_settings, "document_bucket", "documents"),
        help="Bucket or directory name for storing documents (default from env_settings).",
    )
    parser.add_argument(
        "--image-bucket",
        type=str,
        default=getattr(env_settings, "image_bucket", "images"),
        help="Bucket or directory name for storing images (default from env_settings).",
    )
    parser.add_argument(
        "--llamaparse-api-key",
        type=str,
        default=getattr(env_settings, "llamaparse_api_key", ""),
        help="API key for the LlamaParse service (default from env_settings).",
    )
    parser.add_argument(
        "--vector-table",
        type=str,
        default="multimodal_rag_test",
        help="Table name for the PGVectorStore.",
    )
    return parser.parse_args()


async def run_ingestion(args: argparse.Namespace) -> None:
    """Run the ingestion process based on the provided arguments.

    Args:
        args (argparse.Namespace): Parsed CLI arguments.
    """
    pgvector_settings = PgVectorSettings(
        pgvector_connection_string=env_settings.pgvector_connection_string
    )
    vector_store: PGVectorStore = PGVectorStore.from_params(
        host=env_settings.pgvector_host,
        port=str(env_settings.pgvector_port),
        table_name=args.vector_table,
        schema_name="llamaindex_vectorstore",
        user=pgvector_settings.pgvector_username,
        password=pgvector_settings.pgvector_password,
        database=pgvector_settings.pgvector_database,
        embed_dim=1536,
    )
    vector_store.add([])

    fs = LocalFileSystem()

    pdf_path: Path = args.pdf
    if not pdf_path.exists() or not pdf_path.is_file():
        syslog.error(f"PDF file not found: {pdf_path}")
        return

    with open(pdf_path, "rb") as f:
        file_content: bytes = f.read()
    file_key: str = f"{uuid.uuid4()}.pdf"
    with fs.open(f"{args.document_bucket}/{file_key}", "wb+") as remote_file:
        remote_file.write(file_content)
    print(f"Uploaded document to: {file_key}")

    text_llm = get_llm_instance("gpt-4o-mini")
    multimodal_llm = get_llm_instance("gpt-4o")
    embed_model = get_embedding_instance()

    ingestor = DocumentIngestor(
        vector_store=vector_store,
        fs=fs,
        document_bucket_name=args.document_bucket,
        image_bucket_name=args.image_bucket,
        llamaparse_api_key=args.llamaparse_api_key,
        text_llm=text_llm,
        multimodal_llm=multimodal_llm,
        embed_model=embed_model
    )
    index = await ingestor.ingest(file_key)
    syslog.info(f"Ingestion complete. Index: {index}")


def main() -> None:
    """Main entry point for the ingestion CLI."""
    nest_asyncio.apply()
    args = parse_args()
    asyncio.run(run_ingestion(args))


if __name__ == "__main__":
    main()

