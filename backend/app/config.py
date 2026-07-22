from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    PROJECT_NAME: str = "SentinelAI"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "AI-Powered API & LLM Security Scanner"

    DATABASE_URL: str = "sqlite:///./sentinelai.db"

    SECRET_KEY: str = "sentinelai-dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    OLLAMA_URL: str = "http://localhost:11434/api/generate"
    OLLAMA_MODEL: str = "mistral"

    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000", "http://localhost:8080"]
    CORS_ALLOW_ALL: bool = False

    MAX_UPLOAD_SIZE_MB: int = 5
    RATE_LIMIT_PER_MINUTE: int = 30

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
