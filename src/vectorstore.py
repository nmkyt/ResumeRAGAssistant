from functools import lru_cache

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

from src.config import Settings

COLLECTION_NAME = "resumes"


@lru_cache(maxsize=1)
def _load_embeddings(model_name: str, device: str) -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={"device": device},
        encode_kwargs={"normalize_embeddings": True},
    )


def get_embeddings(settings: Settings) -> HuggingFaceEmbeddings:
    return _load_embeddings(settings.embedding_model, settings.embedding_device)


def _open(settings: Settings) -> Chroma:
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=get_embeddings(settings),
        persist_directory=str(settings.index_dir),
        collection_metadata={"hnsw:space": "cosine"},
    )


def build_index(chunks: list[Document], settings: Settings) -> Chroma:
    """Пересобирает индекс с нуля по переданным чанкам (хранится в INDEX_DIR)."""
    db = _open(settings)
    db.reset_collection()
    db.add_documents(chunks)
    return db


def index_exists(settings: Settings) -> bool:
    return (settings.index_dir / "chroma.sqlite3").exists()


def load_index(settings: Settings) -> Chroma:
    if not index_exists(settings):
        raise FileNotFoundError(
            f"Индекс не найден в {settings.index_dir}. Сначала выполните `resume-rag ingest`."
        )
    return _open(settings)
