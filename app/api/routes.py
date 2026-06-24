from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.api.schemas import AskRequest, ClassifyRequest, IngestRequest
from app.classification import classify_text
from app.config import settings
from app.db import SQLiteStore
from app.ingestion import IngestionPipeline
from app.rag import LocalRAG
from app.sources import get_sources

router = APIRouter()


def get_store() -> SQLiteStore:
    settings.ensure_dirs()
    return SQLiteStore(settings.database_path)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}


@router.get("/sources")
def list_sources() -> list[dict]:
    return [source.__dict__ for source in get_sources()]


@router.post("/ingest")
def ingest(payload: IngestRequest) -> dict:
    report = IngestionPipeline(get_store()).run(
        source_ids=payload.source_ids,
        limit_per_source=payload.limit_per_source,
        rebuild_rag=payload.rebuild_rag,
    )
    return report.to_dict()


@router.get("/articles")
def list_articles(
    category: str | None = Query(default=None),
    source_id: str | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
) -> list[dict]:
    return [
        article.to_dict()
        for article in get_store().list_articles(
            category=category,
            source_id=source_id,
            search=search,
            limit=limit,
        )
    ]


@router.get("/articles/{article_id}")
def get_article(article_id: int) -> dict:
    article = get_store().get_article(article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return article.to_dict()


@router.post("/classify")
def classify(payload: ClassifyRequest) -> dict:
    result = classify_text(payload.title, payload.summary, payload.content)
    return {
        "category": result.category,
        "confidence": result.confidence,
        "effective_date": result.effective_date.isoformat() if result.effective_date else None,
        "impact_level": result.impact_level,
        "reasons": list(result.reasons),
    }


@router.post("/rag/rebuild")
def rebuild_rag() -> dict:
    return LocalRAG(settings.database_path).rebuild_index()


@router.post("/rag/ask")
def ask(payload: AskRequest) -> dict:
    return LocalRAG(settings.database_path).answer(payload.query, top_k=payload.top_k)
