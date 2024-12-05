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
    SQLALCHEMY_POSTGRES_URI: str
    SQLALCHEMY_ECHO: bool


class RedisSettings(BaseSettings):
    REDIS_URL: str


class Settings(
    CoreSettings,
    TestSettings,
    DatabaseSettings,
    RedisSettings,
):
    pass


class DevelopmentSettings(Settings):
    pass


class ProductionSettings(Settings):
    DEBUG: bool = False


def get_settings() -> Settings:
    env = os.getenv("ENV", "development")
    setting_types = {
        "development": DevelopmentSettings(),
        "production": ProductionSettings(),
    }
    return setting_types[env]


settings = get_settings()
