from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения. Читаются из переменных окружения и файла .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Пути
    resumes_dir: Path = Path("data/resumes")
    index_dir: Path = Path("data/index")

    # Чанкинг
    chunk_size: int = 800
    chunk_overlap: int = 150

    # Эмбеддинги: модель должна понимать русский язык
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_device: str = "cpu"

    # Поиск
    search_top_k: int = 5

    # LLM (любой OpenAI-совместимый API, по умолчанию DeepSeek)
    llm_model: str = "deepseek-chat"
    llm_base_url: str = "https://api.deepseek.com"
    llm_api_key: SecretStr | None = None
    llm_temperature: float = 0.0

    # API hh.ru (нужен токен работодателя с доступом к базе резюме)
    hh_api_url: str = "https://api.hh.ru"
    hh_access_token: SecretStr | None = None
    hh_user_agent: str = "ResumeRAGAssistant/0.1 (example@example.com)"


@lru_cache
def get_settings() -> Settings:
    return Settings()
