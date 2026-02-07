from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """환경 변수 기반 설정."""
    openai_api_key: str = ""
    environment: str = "development"
    model_name: str = "gpt-4o"

    class Config:
        env_file = ".env"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
