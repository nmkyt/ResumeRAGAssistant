"""Клиент API hh.ru для выгрузки резюме.

Поиск по базе резюме доступен только работодателю с купленным доступом:
нужен OAuth-токен работодателя (HH_ACCESS_TOKEN). Каждый просмотр полного
резюме (GET /resumes/{id}) списывается из лимита просмотров работодателя.
Документация: https://api.hh.ru/openapi/redoc
"""

import json
import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx

from src.config import Settings

logger = logging.getLogger(__name__)


class HHClient:
    def __init__(self, settings: Settings):
        if settings.hh_access_token is None:
            raise RuntimeError("Не задан HH_ACCESS_TOKEN (см. .env.example)")
        self._client = httpx.Client(
            base_url=settings.hh_api_url,
            headers={
                "Authorization": f"Bearer {settings.hh_access_token.get_secret_value()}",
                "HH-User-Agent": settings.hh_user_agent,
            },
            timeout=30,
        )

    def __enter__(self) -> "HHClient":
        return self

    def __exit__(self, *exc) -> None:
        self._client.close()

    def search(self, text: str, area: str | None = None, limit: int = 50) -> Iterator[dict]:
        """Ищет резюме и отдаёт краткие карточки из выдачи (без полного текста)."""
        per_page = min(limit, 100)
        page, found = 0, 0
        while found < limit:
            params: dict[str, Any] = {"text": text, "per_page": per_page, "page": page}
            if area:
                params["area"] = area
            response = self._client.get("/resumes", params=params)
            response.raise_for_status()
            data = response.json()
            for item in data["items"]:
                yield item
                found += 1
                if found >= limit:
                    return
            page += 1
            if page >= data["pages"]:
                return

    def get_resume(self, resume_id: str) -> dict:
        response = self._client.get(f"/resumes/{resume_id}")
        response.raise_for_status()
        return response.json()

    def download(self, text: str, out_dir: Path, area: str | None = None, limit: int = 50) -> int:
        """Скачивает полные резюме по запросу в out_dir/<id>.json. Уже скачанные пропускает."""
        out_dir.mkdir(parents=True, exist_ok=True)
        saved = 0
        for item in self.search(text, area=area, limit=limit):
            path = out_dir / f"{item['id']}.json"
            if path.exists():
                continue
            try:
                resume = self.get_resume(item["id"])
            except httpx.HTTPStatusError as e:
                logger.warning("Не удалось получить резюме %s: %s", item["id"], e)
                continue
            path.write_text(json.dumps(resume, ensure_ascii=False, indent=2), encoding="utf-8")
            saved += 1
        return saved
