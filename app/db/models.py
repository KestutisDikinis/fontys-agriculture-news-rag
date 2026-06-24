from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone


@dataclass(frozen=True)
class Article:
    source_id: str
    title: str
    url: str
    summary: str = ""
    content: str = ""
    published_at: datetime | None = None
    category: str = "background_news"
    confidence: float = 0.0
    effective_date: date | None = None
    impact_level: str = "medium"
    created_at: datetime | None = None
    id: int | None = None

    @property
    def searchable_text(self) -> str:
        return "\n\n".join(part for part in [self.title, self.summary, self.content] if part)

    def to_dict(self) -> dict:
        created = self.created_at or datetime.now(timezone.utc)
        return {
            "id": self.id,
            "source_id": self.source_id,
            "title": self.title,
            "url": self.url,
            "summary": self.summary,
            "content": self.content,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "category": self.category,
            "confidence": self.confidence,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "impact_level": self.impact_level,
            "created_at": created.isoformat(),
        }
