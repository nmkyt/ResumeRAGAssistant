from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from src.config import Settings
from src.search import ResumeHit

SYSTEM_PROMPT = """Ты ассистент рекрутера. Тебе дают фрагменты резюме кандидатов с hh.ru.
Отвечай ТОЛЬКО на основе этих фрагментов. Если информации недостаточно — так и скажи:
«Не найдено в резюме». Когда упоминаешь кандидата, указывай номер резюме в квадратных
скобках, например [2]. Отвечай на русском языке."""

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("human", "Резюме:\n{context}\n\nВопрос: {question}"),
    ]
)


def build_llm(settings: Settings) -> ChatOpenAI:
    if settings.llm_api_key is None:
        raise RuntimeError("Не задан LLM_API_KEY (см. .env.example)")
    return ChatOpenAI(
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        temperature=settings.llm_temperature,
    )


def format_context(hits: list[ResumeHit]) -> str:
    blocks = []
    for i, hit in enumerate(hits, start=1):
        header = f"[{i}] {hit.title or 'Без названия'}"
        if hit.area:
            header += f", {hit.area}"
        fragments = "\n...\n".join(chunk.page_content for chunk in hit.fragments)
        blocks.append(f"{header}\n{fragments}")
    return "\n\n---\n\n".join(blocks)


def answer_question(question: str, hits: list[ResumeHit], settings: Settings) -> str:
    """Генерирует ответ LLM по найденным резюме."""
    if not hits:
        return "Не найдено в резюме"
    chain = prompt | build_llm(settings) | StrOutputParser()
    return chain.invoke({"context": format_context(hits), "question": question})
