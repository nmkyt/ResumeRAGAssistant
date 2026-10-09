"""Загрузка резюме hh.ru: выгрузки PDF/DOCX/TXT и JSON из API hh.ru.

Каждое резюме превращается в один Document с метаданными
(resume_id, title, candidate, area, source), дальше он режется на чанки.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any

import docx2txt
from langchain_core.documents import Document
from pypdf import PdfReader

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".json"}

_MONTHS = {
    1: "январь",
    2: "февраль",
    3: "март",
    4: "апрель",
    5: "май",
    6: "июнь",
    7: "июль",
    8: "август",
    9: "сентябрь",
    10: "октябрь",
    11: "ноябрь",
    12: "декабрь",
}


def load_resumes(directory: Path) -> list[Document]:
    """Рекурсивно загружает все поддерживаемые резюме из директории."""
    documents = []
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        try:
            documents.append(load_resume(path))
        except Exception:
            logger.exception("Не удалось загрузить резюме %s", path)
    return documents


def load_resume(path: Path) -> Document:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return hh_json_to_document(json.loads(path.read_text(encoding="utf-8")), source=str(path))

    if suffix == ".pdf":
        text = "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
    elif suffix == ".docx":
        text = docx2txt.process(str(path))
    elif suffix == ".txt":
        text = path.read_text(encoding="utf-8")
    else:
        raise ValueError(f"Неподдерживаемый формат: {path.suffix}")

    text = _normalize_text(text)
    return Document(
        page_content=text,
        metadata={"resume_id": path.stem, "source": str(path), **parse_hh_export(text)},
    )


def parse_hh_export(text: str) -> dict[str, str]:
    """Достаёт ключевые поля из текста резюме, выгруженного с hh.ru в PDF/DOCX."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    meta = {"candidate": lines[0] if lines else "", "title": "", "area": ""}

    for i, line in enumerate(lines):
        if line.startswith("Желаемая должность") and i + 1 < len(lines):
            meta["title"] = lines[i + 1]
        elif line.startswith("Проживает:"):
            meta["area"] = line.removeprefix("Проживает:").strip()
    return meta


def hh_json_to_document(resume: dict[str, Any], source: str = "") -> Document:
    """Превращает резюме из API hh.ru (GET /resumes/{id}) в Document."""
    candidate = " ".join(
        part for part in (resume.get("last_name"), resume.get("first_name")) if part
    )
    area = _name(resume.get("area"))
    title = resume.get("title") or ""

    sections = [f"Желаемая должность: {title}"]
    if candidate:
        sections.append(f"Кандидат: {candidate}")
    if resume.get("age"):
        sections.append(f"Возраст: {resume['age']}")
    if area:
        sections.append(f"Город: {area}")
    if salary := resume.get("salary"):
        sections.append(f"Зарплата: {salary.get('amount')} {salary.get('currency', '')}".strip())
    if roles := _names(resume.get("professional_roles")):
        sections.append(f"Специализации: {roles}")
    if total := (resume.get("total_experience") or {}).get("months"):
        sections.append(f"Общий опыт: {_format_months(total)}")

    if experience := resume.get("experience"):
        jobs = []
        for job in experience:
            period = f"{_format_date(job.get('start'))} — {_format_date(job.get('end'))}"
            header = f"{period}, {job.get('company') or ''}: {job.get('position') or ''}"
            jobs.append("\n".join(filter(None, [header, (job.get("description") or "").strip()])))
        sections.append("Опыт работы:\n" + "\n\n".join(jobs))

    if skill_set := resume.get("skill_set"):
        sections.append("Навыки: " + ", ".join(skill_set))
    if about := resume.get("skills"):
        sections.append(f"О себе:\n{about.strip()}")

    education = resume.get("education") or {}
    if primary := education.get("primary"):
        items = [
            ", ".join(str(v) for v in (e.get("year"), e.get("name"), e.get("result")) if v)
            for e in primary
        ]
        level = _name(education.get("level"))
        sections.append(f"Образование ({level}):\n" + "\n".join(items))

    if languages := resume.get("language"):
        langs = [f"{lang.get('name')} — {_name(lang.get('level'))}" for lang in languages]
        sections.append("Языки: " + "; ".join(langs))

    return Document(
        page_content=_normalize_text("\n\n".join(sections)),
        metadata={
            "resume_id": str(resume.get("id", "")),
            "source": resume.get("alternate_url") or source,
            "candidate": candidate,
            "title": title,
            "area": area,
        },
    )


def _name(item: dict | None) -> str:
    return (item or {}).get("name", "")


def _names(items: list[dict] | None) -> str:
    return ", ".join(item["name"] for item in items or [] if item.get("name"))


def _format_date(value: str | None) -> str:
    if not value:
        return "по настоящее время"
    year, month, *_ = value.split("-")
    return f"{_MONTHS.get(int(month), month)} {year}"


def _format_months(months: int) -> str:
    years, rest = divmod(months, 12)
    return " ".join(filter(None, [f"{years} г." if years else "", f"{rest} мес." if rest else ""]))


def _normalize_text(text: str) -> str:
    text = text.replace(" ", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()
