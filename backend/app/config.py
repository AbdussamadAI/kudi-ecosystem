from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "KudiCore API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/kudi"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # AI / LLM
    GROQ_API_KEY: str = ""
    TOGETHER_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    LLM_PROVIDER: str = "openrouter"  # "groq" or "openrouter"
    LLM_MODEL: str = "meta-llama/llama-3.1-70b-instruct"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    ASSISTANT_ENABLE_RAG: bool = False
    ASSISTANT_MAX_OUTPUT_TOKENS: int = 600
    ASSISTANT_MAX_OUTPUT_WORDS: int = 180

    # Payments
    PAYSTACK_SECRET_KEY: str = ""
    PAYSTACK_PUBLIC_KEY: str = ""
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLIC_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # Rate Limiting
    FREE_TIER_CHAT_LIMIT: int = 10
    FREE_TIER_TRANSACTION_LIMIT: int = 50
    FREE_TIER_SCENARIO_LIMIT: int = 3

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
