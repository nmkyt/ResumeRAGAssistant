"""CLI: resume-rag ingest | search | ask | fetch-hh | serve."""

import argparse
import logging
import sys

from src.config import get_settings


def cmd_ingest(_: argparse.Namespace) -> None:
    from src.ingestion import split_resumes
    from src.loaders import load_resumes
    from src.vectorstore import build_index

    settings = get_settings()
    resumes = load_resumes(settings.resumes_dir)
    if not resumes:
        sys.exit(f"Нет резюме в {settings.resumes_dir}")
    chunks = split_resumes(resumes, settings)
    build_index(chunks, settings)
    print(f"Проиндексировано резюме: {len(resumes)}, чанков: {len(chunks)} -> {settings.index_dir}")


def _search(args: argparse.Namespace):
    from src.search import search_resumes
    from src.vectorstore import load_index

    settings = get_settings()
    return search_resumes(load_index(settings), args.query, args.top_k or settings.search_top_k)


def cmd_search(args: argparse.Namespace) -> None:
    for i, hit in enumerate(_search(args), start=1):
        print(f"[{i}] {hit.score:.3f}  {hit.title or '—'}  {hit.area}  ({hit.source})")
        print("    " + hit.fragments[0].page_content[:300].replace("\n", " "))


def cmd_ask(args: argparse.Namespace) -> None:
    from src.qa_chain import answer_question

    hits = _search(args)
    print(answer_question(args.query, hits, get_settings()))
    print("\nИсточники:")
    for i, hit in enumerate(hits, start=1):
        print(f"[{i}] {hit.title or '—'} ({hit.source})")


def cmd_fetch_hh(args: argparse.Namespace) -> None:
    from src.hh_client import HHClient

    settings = get_settings()
    out_dir = settings.resumes_dir / "hh"
    with HHClient(settings) as client:
        saved = client.download(args.query, out_dir, area=args.area, limit=args.limit)
    print(f"Скачано новых резюме: {saved} -> {out_dir}")


def cmd_serve(args: argparse.Namespace) -> None:
    import uvicorn

    uvicorn.run("src.api:app", host=args.host, port=args.port, reload=args.reload)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(prog="resume-rag", description="RAG-поиск по резюме hh.ru")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("ingest", help="проиндексировать резюме из RESUMES_DIR").set_defaults(
        func=cmd_ingest
    )

    for name, func, help_text in (
        ("search", cmd_search, "найти подходящие резюме"),
        ("ask", cmd_ask, "задать вопрос по базе резюме (нужен LLM_API_KEY)"),
    ):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("query")
        p.add_argument("-k", "--top-k", type=int, default=None)
        p.set_defaults(func=func)

    p = sub.add_parser("fetch-hh", help="скачать резюме через API hh.ru (нужен HH_ACCESS_TOKEN)")
    p.add_argument("query", help="поисковый запрос, например 'python developer'")
    p.add_argument("--area", help="id региона hh.ru (1 — Москва, 2 — Санкт-Петербург)")
    p.add_argument("--limit", type=int, default=50)
    p.set_defaults(func=cmd_fetch_hh)

    p = sub.add_parser("serve", help="запустить HTTP API")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--reload", action="store_true")
    p.set_defaults(func=cmd_serve)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
