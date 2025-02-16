from typing import Optional
from urllib.parse import urlparse
from pydantic_settings import BaseSettings


class PgVectorSettings(BaseSettings):
    pgvector_connection_string: str

    @property
    def pgvector_host(self) -> str:
        return urlparse(self.pgvector_connection_string).hostname or ""

    @property
    def pgvector_port(self) -> int:
        return urlparse(self.pgvector_connection_string).port or 5432  # Default PostgreSQL port

    @property
    def database(self) -> str:
        return urlparse(self.pgvector_connection_string).path.lstrip('/') or ""

    @property
    def username(self) -> str:
        parsed_value = urlparse(self.pgvector_connection_string).username
        if parsed_value is None:
            raise ValueError("Username is missing in the connection string")
        return parsed_value

    @property
    def password(self) -> str:
        parsed_value = urlparse(self.pgvector_connection_string).password
        if parsed_value is None:
            raise ValueError("Password is missing in the connection string")
        return parsed_value

    @property
    def pgvector_async_connection_string(self) -> str:
        """
        Convert the standard PostgreSQL connection string to an async-compatible version for asyncpg.
        """
        parsed_url = urlparse(self.pgvector_connection_string)
        return (
            f"postgresql+asyncpg://{parsed_url.username}:{parsed_url.password}"
            f"@{parsed_url.hostname}:{parsed_url.port}{parsed_url.path}"
        )

class CoreSettings(BaseSettings):
    pdf_path: str = "paper.pdf"
    image_download_dir: str = "paper_images"
    storage_dir_index: str = "paper_nodes"
    storage_dir_index_base: str = "paper_nodes_base"
    llama_parse_result_type: str = "markdown"
    fsspec_protocol: str = "file"
    vector_index_id: str = "vector_index"
    multimodal_model: str = "gpt-4o"
    multimodal_max_new_tokens: int = 4096
    host: str = "localhost"
    port: int = 8080
    debug: bool = True
    sqlalchemy_postgres_uri: str
    openai_api_key: str
    llamaparse_api_key: str

class AppSettings(CoreSettings, PgVectorSettings):
    class Config:
        env_file = ".env"

env_settings = AppSettings()
