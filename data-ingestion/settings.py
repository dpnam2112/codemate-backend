from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    pdf_path: str = "paper.pdf"
    image_download_dir: str = "paper_images"
    storage_dir_index: str = "paper_nodes"
    storage_dir_index_base: str = "paper_nodes_base"
    llama_parse_result_type: str = "markdown"
    fsspec_protocol: str = "file"
    vector_index_id: str = "vector_index"
    multimodal_model: str = "gpt-4o"
    multimodal_max_new_tokens: int = 4096
    pgvector_connection_string: str
    pgvector_async_connection_string: str
    openai_api_key: str
    llamaparse_api_key: str

    class Config:
        env_file = ".env"

env_settings = AppSettings()
