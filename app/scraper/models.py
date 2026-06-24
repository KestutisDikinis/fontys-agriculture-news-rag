from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, field_validator


class ScrapeStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class ScrapedArticle(BaseModel):
    """Normalized article/update emitted by any scraper.

    All scraper implementations should return this shape so ingestion,
    classification, RAG, and summarization can stay scraper-agnostic.
    """

    id: str = Field(min_length=16)
    source_id: str = Field(min_length=3)
    title: str = Field(min_length=1)
    url: HttpUrl
    published_at: datetime | None = None
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    author: str | None = None
    summary: str | None = None
    content: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)

    @field_validator("published_at", "fetched_at")
    @classmethod
    def ensure_timezone(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class ScrapeResult(BaseModel):
    """Result of scraping exactly one source."""

    source_id: str
    status: ScrapeStatus
    articles: list[ScrapedArticle] = Field(default_factory=list)
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.status == ScrapeStatus.SUCCESS
