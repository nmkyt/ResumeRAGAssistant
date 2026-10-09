from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from src.config import get_settings
from src.ingestion import split_resumes
from src.loaders import load_resumes
from src.qa_chain import answer_question
from src.search import ResumeHit, search_resumes
from src.vectorstore import build_index, index_exists, load_index

settings = get_settings()
state: dict = {"db": None}


@asynccontextmanager
async def lifespan(_: FastAPI):
    if index_exists(settings):
        state["db"] = await run_in_threadpool(load_index, settings)
    yield


app = FastAPI(title="Resume RAG Assistant", version="0.1.0", lifespan=lifespan)


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, examples=["Python-разработчик с опытом FastAPI и PostgreSQL"])
    top_k: int = Field(default=settings.search_top_k, ge=1, le=50)


class Fragment(BaseModel):
    text: str
    chunk_id: int | None = None


class ResumeResult(BaseModel):
    resume_id: str
    score: float
    title: str
    candidate: str
    area: str
    source: str
    fragments: list[Fragment]


class SearchResponse(BaseModel):
    results: list[ResumeResult]


class AskResponse(SearchResponse):
    answer: str


class IngestResponse(BaseModel):
    resumes: int
    chunks: int


def _to_result(hit: ResumeHit) -> ResumeResult:
    return ResumeResult(
        resume_id=hit.resume_id,
        score=round(hit.score, 4),
        title=hit.title,
        candidate=hit.candidate,
        area=hit.area,
        source=hit.source,
        fragments=[
            Fragment(text=chunk.page_content, chunk_id=chunk.metadata.get("chunk_id"))
            for chunk in hit.fragments
        ],
    )


def _search(request: SearchRequest) -> list[ResumeHit]:
    if state["db"] is None:
        raise HTTPException(status_code=409, detail="Индекс пуст. Вызовите POST /ingest.")
    return search_resumes(state["db"], request.query, request.top_k)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "index_loaded": state["db"] is not None}


@app.post("/ingest", response_model=IngestResponse)
def ingest() -> IngestResponse:
    """Переиндексирует все резюме из RESUMES_DIR."""
    resumes = load_resumes(settings.resumes_dir)
    if not resumes:
        raise HTTPException(status_code=400, detail=f"Нет резюме в {settings.resumes_dir}")
    chunks = split_resumes(resumes, settings)
    state["db"] = build_index(chunks, settings)
    return IngestResponse(resumes=len(resumes), chunks=len(chunks))


@app.post("/search", response_model=SearchResponse)
def search(request: SearchRequest) -> SearchResponse:
    """Семантический поиск подходящих резюме без LLM."""
    return SearchResponse(results=[_to_result(hit) for hit in _search(request)])


@app.post("/ask", response_model=AskResponse)
def ask(request: SearchRequest) -> AskResponse:
    """Вопрос по базе резюме: поиск + ответ LLM с указанием кандидатов."""
    hits = _search(request)
    try:
        answer = answer_question(request.query, hits, settings)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    return AskResponse(answer=answer, results=[_to_result(hit) for hit in hits])
