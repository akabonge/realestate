from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path

_ENV_FILE = Path(__file__).parent.parent / ".env"


class Settings(BaseSettings):
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-haiku-4-5-20251001"

    ollama_model: str = "llama3.2"
    ollama_base_url: str = "http://localhost:11434"

    chroma_persist_path: str = str(Path(__file__).parent.parent / "chroma_store")
    chroma_collection_name: str = "realty_docs"

    embedding_model: str = "all-MiniLM-L6-v2"

    max_retrieved_chunks: int = 6
    max_history_messages: int = 12

    leads_file: str = str(Path(__file__).parent.parent / "leads.json")

    class Config:
        env_file = str(_ENV_FILE)


@lru_cache
def get_settings() -> Settings:
    return Settings()
