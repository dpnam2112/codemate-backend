from typing import Optional
from pydantic_settings import BaseSettings

class TestSettings(BaseSettings):
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None

    class Config:
        env_file = ".env"
        extra = "allow"

test_settings = TestSettings()

