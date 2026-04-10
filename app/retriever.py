
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS


def build_vectorstore(chunks):
    """
    Создаёт векторную базу из текстовых чанков
    """

    # 1. Модель эмбеддингов
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    # 2. Создание FAISS индекса
    db = FAISS.from_documents(chunks, embeddings)

    return db


def get_retriever(db):
    return db.as_retriever(
        search_kwargs={"k": 3}
    )