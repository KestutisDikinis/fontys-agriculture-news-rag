from __future__ import annotations

from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    source_ids: list[str] | None = None
    limit_per_source: int = Field(default=20, ge=1, le=200)
    rebuild_rag: bool = True


class AskRequest(BaseModel):
    query: str = Field(min_length=2)
    top_k: int = Field(default=5, ge=1, le=20)


class ClassifyRequest(BaseModel):
    title: str = Field(min_length=1)
    summary: str = ""
    content: str = ""


class ArticleResponse(BaseModel):
    id: int | None
    source_id: str
    title: str
    url: str
    summary: str
    content: str
    published_at: str | None
    category: str
    confidence: float
    effective_date: str | None
    impact_level: str
    created_at: str
