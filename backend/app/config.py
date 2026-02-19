from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env")

    # App
    APP_NAME: str = "Code Archaeologist"
    DEBUG: bool = False

    # CORS Configuration
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Database
    DATABASE_URL: str = "sqlite:///./codearch.db"

    # LLM (Ollama-compatible OpenAI API)
    OPENAI_API_KEY: str = "ollama"
    OPENAI_BASE_URL: str = "http://localhost:11434/v1"
    OPENAI_MODEL: str = "deepseek-coder-v2:16b"
    OPENAI_TEMPERATURE: float = 0.3

    # Local Embeddings
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSIONS: int = 384

    # Batching
    LLM_BATCH_SIZE: int = 5
    LLM_MAX_CONCURRENT: int = 2

    # Vector Store
    VECTOR_DB_DIR: str = "./vector_db"

    # GitHub
    GITHUB_TOKEN: str = ""
    GITHUB_ALLOWED_DOMAINS: list[str] = ["github.com", "gitlab.com"]

    # Repository Storage
    REPO_CLONE_DIR: str = "./cloned_repos"
    REPO_CACHE_TTL: int = 3600  # 1 hour

    # Feature Flags
    ENABLE_RELATIONSHIP_DETECTION: bool = True
    ENABLE_CACHING: bool = True
    MAX_REPO_SIZE_MB: int = 500
    MAX_FILE_SIZE_MB: int = 10

    # Analysis Configuration
    BATCH_SIZE: int = 10
    RAG_RESULTS_LIMIT: int = 8
    MAX_CONCURRENT_TASKS: int = 5


@lru_cache()
def get_settings() -> Settings:
    return Settings()
