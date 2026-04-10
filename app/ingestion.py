# app/ingestion.py

from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter


def load_and_split(path: str):
    """
    1. Загружает PDF
    2. Разбивает на чанки
    """

    loader = PyPDFLoader(path)
    documents = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100
    )

    chunks = splitter.split_documents(documents)

    # добавляем метаданные (важно для собеса)
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = i

    return chunks