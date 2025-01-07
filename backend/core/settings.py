from dotenv import load_dotenv
load_dotenv()
import os
from typing import Literal
from pydantic_settings import BaseSettings

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

# Định nghĩa các trường email và JWT settings
class EmailSettings(BaseSettings):
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_PORT: int
    MAIL_SERVER: str
    MAIL_STARTTLS: bool
    MAIL_SSL_TLS: bool
    USE_CREDENTIALS: bool

class JWTSettings(BaseSettings):
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    
class ExcelLinkSettings(BaseSettings):
    EXCEL_FILE_PATH: str

class GoogleAPI(BaseSettings):
    CLIENT_AUTH: str
    GOOGLE_API_URL: str

class Settings(
    CoreSettings,
    TestSettings,
    DatabaseSettings,
    RedisSettings,
    EmailSettings,
    JWTSettings,
    ExcelLinkSettings,
    GoogleAPI
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
