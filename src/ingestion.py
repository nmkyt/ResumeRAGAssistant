from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import Settings


def split_resumes(resumes: list[Document], settings: Settings) -> list[Document]:
    """Режет резюме на чанки.

    В начало каждого чанка добавляется заголовок резюме (должность и город),
    чтобы фрагмент вроде «5 лет опыта с Kubernetes» не терял связь с кандидатом.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    chunks = []
    for resume in resumes:
        header = _resume_header(resume)
        for i, chunk in enumerate(splitter.split_documents([resume])):
            chunk.metadata["chunk_id"] = i
            if header:
                chunk.page_content = f"{header}\n{chunk.page_content}"
            chunks.append(chunk)
    return chunks


def _resume_header(resume: Document) -> str:
    title = resume.metadata.get("title")
    area = resume.metadata.get("area")
    if not title:
        return ""
    return f"[Резюме: {title}{f', {area}' if area else ''}]"
