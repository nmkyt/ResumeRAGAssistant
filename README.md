# Resume RAG Assistant

RAG-поиск по резюме с [hh.ru](https://hh.ru): загружает резюме, индексирует их в векторной базе
и позволяет искать подходящих кандидатов по запросу на естественном языке
(«Python-разработчик с опытом Kafka в Москве») и задавать вопросы LLM по найденным резюме.

## Как это работает

```
резюме (PDF / DOCX / TXT / JSON из API hh.ru)
  → src/loaders.py      одно резюме = один документ + метаданные (должность, город, кандидат)
  → src/ingestion.py    разбиение на чанки, к каждому чанку добавляется заголовок резюме
  → src/vectorstore.py  эмбеддинги (multilingual sentence-transformers) → Chroma на диске
  → src/search.py       поиск чанков, группировка по резюме, ранжирование кандидатов
  → src/qa_chain.py     ответ LLM (DeepSeek / любой OpenAI-совместимый API) со ссылками на резюме
```

## Структура

```
src/            код приложения (FastAPI, CLI, RAG-пайплайн, клиент API hh.ru)
tests/          тесты
infra/          Dockerfile, docker-compose, .dockerignore
data/resumes/   резюме для индексации (в git не попадают)
data/index/     векторный индекс Chroma (создаётся командой ingest)
```

## Установка

Нужен [uv](https://docs.astral.sh/uv/).

```bash
uv sync
cp .env.example .env   # и заполнить LLM_API_KEY
```

## Источники резюме

1. **Выгрузки с сайта.** Скачайте резюме с hh.ru (PDF, DOCX или TXT) и положите в `data/resumes/`.
2. **API hh.ru.** Нужен OAuth-токен работодателя с доступом к базе резюме (`HH_ACCESS_TOKEN`).
   Каждое скачанное полное резюме списывается из лимита просмотров работодателя.

   ```bash
   uv run resume-rag fetch-hh "python developer" --area 1 --limit 50
   ```

   Резюме сохраняются в `data/resumes/hh/<id>.json`.

Содержимое `data/` в git не попадает: резюме содержат персональные данные.

## Использование

```bash
uv run resume-rag ingest                                  # построить индекс
uv run resume-rag search "ML-инженер с опытом NLP"        # найти резюме
uv run resume-rag ask "У кого есть опыт с Kubernetes?"    # ответ LLM
```

### HTTP API

```bash
uv run uvicorn src.api:app --reload
```

Документация Swagger: http://127.0.0.1:8000/docs

| Метод | Путь      | Описание                                    |
|-------|-----------|---------------------------------------------|
| GET   | `/health` | статус и наличие индекса                    |
| POST  | `/ingest` | переиндексировать `data/resumes`            |
| POST  | `/search` | `{"query": "...", "top_k": 5}` — резюме     |
| POST  | `/ask`    | то же + ответ LLM                           |

### Docker

```bash
docker compose -f infra/docker-compose.yml up --build
```

## Разработка

```bash
uv run pytest
uv run ruff check .
uv run ruff format .
```

Добавить зависимость: `uv add <пакет>` (dev-зависимость: `uv add --dev <пакет>`).
Если нужен `requirements.txt` для pip: `uv export --no-dev --no-hashes -o requirements.txt`.
