from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Define your settings with defaults and corresponding environment variable names
    HOST: str
    PORT: int
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "FATAL"] = "DEBUG"
    DEBUG: bool
    POSTGRES_PGVECTOR_DB_URI: str

    # Use the new configuration syntax in Pydantic v2
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

# Instantiate the settings; this will load variables from .env
env_settings = Settings()
