from dataclasses import dataclass, field

from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore


@dataclass
class ResumeHit:
    """Резюме, найденное по запросу, с наиболее релевантными фрагментами."""

    resume_id: str
    score: float
    title: str = ""
    candidate: str = ""
    area: str = ""
    source: str = ""
    fragments: list[Document] = field(default_factory=list)


def search_resumes(db: VectorStore, query: str, top_k: int = 5) -> list[ResumeHit]:
    """Ищет резюме, а не отдельные чанки.

    Берём с запасом чанков, группируем по resume_id, резюме ранжируем
    по лучшему фрагменту.
    """
    scored_chunks = db.similarity_search_with_relevance_scores(query, k=top_k * 5)

    hits: dict[str, ResumeHit] = {}
    for chunk, score in scored_chunks:
        meta = chunk.metadata
        resume_id = meta.get("resume_id") or meta.get("source", "")
        hit = hits.get(resume_id)
        if hit is None:
            hit = hits[resume_id] = ResumeHit(
                resume_id=resume_id,
                score=score,
                title=meta.get("title", ""),
                candidate=meta.get("candidate", ""),
                area=meta.get("area", ""),
                source=meta.get("source", ""),
            )
        hit.score = max(hit.score, score)
        hit.fragments.append(chunk)

    return sorted(hits.values(), key=lambda h: h.score, reverse=True)[:top_k]
