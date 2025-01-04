import os
from typing import Literal
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class CoreSettings(BaseSettings):
    ENV: Literal["development", "production"] = "development"
    DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8080
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARN", "ERROR", "FATAL"] = "DEBUG"


class TestSettings(BaseSettings):
    PYTEST: bool = False
    PYTEST_UNIT: bool = False


class DatabaseSettings(BaseSettings):
    SQLALCHEMY_POSTGRES_URI: str = "postgresql+asyncpg://nam:123@127.0.0.1:5432/edu"
    SQLALCHEMY_ECHO: bool = False


class RedisSettings(BaseSettings):
    REDIS_URL: str = "redis://localhost:6379"

class Neo4jSettings(BaseSettings):
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = "password"

class GoogleGenAISettings(BaseSettings):
    GOOGLE_GENAI_API_KEY: str

class OpenAISettings(BaseSettings):
    OPENAI_API_KEY: str = ""


class Settings(
    CoreSettings,
    TestSettings,
    DatabaseSettings,
    RedisSettings,
    Neo4jSettings,
    GoogleGenAISettings,
    OpenAISettings
): ...


class DevelopmentSettings(Settings):
    pass


class ProductionSettings(Settings):
    DEBUG: bool = False


def get_settings() -> Settings:
    source = {"_env_file": ".env", "_env_file_encoding": "utf-8"}
    env = os.getenv("ENV", "development")
    setting_types = {
        "development": DevelopmentSettings(**source),
        "production": ProductionSettings(**source),
    }
    return setting_types[env]

settings = get_settings()
