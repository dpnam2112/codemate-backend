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
    SQLALCHEMY_POSTGRES_URI: str = os.getenv("SQLALCHEMY_POSTGRES_URI","")
    SQLALCHEMY_ECHO: bool = os.getenv("SQLALCHEMY_ECHO", False)

class RedisSettings(BaseSettings):
    REDIS_URL: str = "redis://localhost:6379"

class Neo4jSettings(BaseSettings):
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = "password"

class GoogleGenAISettings(BaseSettings):
    GOOGLE_GENAI_API_KEY: str = ""

class OpenAISettings(BaseSettings):
    OPENAI_API_KEY: str = ""

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
    REFRESH_SECRET_KEY: str
    REFRESH_TOKEN_EXPIRE_DAYS: int
    
class ExcelLinkSettings(BaseSettings):
    EXCEL_FILE_PATH: str

class GoogleAPI(BaseSettings):
    CLIENT_AUTH: str
    GOOGLE_API_URL: str
class AWS3Settings(BaseSettings):
    AWS3_ACCESS_KEY_ID: str
    AWS3_SECRET_ACCESS_KEY: str 
    AWS3_REGION: str 
    AWS3_BUCKET_NAME: str
class Settings(
    CoreSettings,
    TestSettings,
    DatabaseSettings,
    RedisSettings,
    EmailSettings,
    JWTSettings,
    ExcelLinkSettings,
    GoogleAPI,
    Neo4jSettings,
    GoogleGenAISettings,
    OpenAISettings,
    AWS3Settings
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
