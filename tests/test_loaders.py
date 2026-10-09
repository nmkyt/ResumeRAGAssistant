from src.config import Settings
from src.ingestion import split_resumes
from src.loaders import hh_json_to_document, parse_hh_export

HH_RESUME = {
    "id": "abc123",
    "title": "Python-разработчик",
    "first_name": "Иван",
    "last_name": "Иванов",
    "age": 30,
    "area": {"name": "Москва"},
    "salary": {"amount": 300000, "currency": "RUR"},
    "total_experience": {"months": 62},
    "professional_roles": [{"name": "Программист, разработчик"}],
    "experience": [
        {
            "company": "Рога и копыта",
            "position": "Backend-разработчик",
            "start": "2021-03-01",
            "end": None,
            "description": "FastAPI, PostgreSQL, Kafka",
        }
    ],
    "skill_set": ["Python", "Docker"],
    "education": {
        "level": {"name": "Высшее"},
        "primary": [{"name": "МГУ", "result": "ВМК", "year": 2017}],
    },
    "language": [{"name": "Английский", "level": {"name": "B2"}}],
    "alternate_url": "https://hh.ru/resume/abc123",
}


def test_hh_json_to_document():
    doc = hh_json_to_document(HH_RESUME)

    assert doc.metadata == {
        "resume_id": "abc123",
        "source": "https://hh.ru/resume/abc123",
        "candidate": "Иванов Иван",
        "title": "Python-разработчик",
        "area": "Москва",
    }
    text = doc.page_content
    assert "Общий опыт: 5 г. 2 мес." in text
    assert "март 2021 — по настоящее время, Рога и копыта: Backend-разработчик" in text
    assert "Навыки: Python, Docker" in text
    assert "Английский — B2" in text


def test_hh_json_handles_missing_fields():
    doc = hh_json_to_document({"id": 1, "title": "Аналитик"})
    assert doc.metadata["resume_id"] == "1"
    assert "Желаемая должность: Аналитик" in doc.page_content


def test_parse_hh_export():
    text = (
        "Петров Пётр\nМужчина\nПроживает: Санкт-Петербург\n"
        "Желаемая должность и зарплата\nML-инженер\nОпыт работы — 3 года"
    )
    assert parse_hh_export(text) == {
        "candidate": "Петров Пётр",
        "title": "ML-инженер",
        "area": "Санкт-Петербург",
    }


def test_chunks_keep_resume_header():
    settings = Settings(chunk_size=100, chunk_overlap=0, _env_file=None)
    chunks = split_resumes([hh_json_to_document(HH_RESUME)], settings)

    assert len(chunks) > 1
    assert all(c.page_content.startswith("[Резюме: Python-разработчик, Москва]") for c in chunks)
    assert [c.metadata["chunk_id"] for c in chunks] == list(range(len(chunks)))
