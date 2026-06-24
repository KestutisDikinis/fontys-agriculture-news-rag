from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, field_validator


class SourceKind(str, Enum):
    RSS = "rss"
    HTML = "html"
    API = "api"


class SourceReliability(str, Enum):
    OFFICIAL = "official"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SourceCategory(str, Enum):
    OFFICIAL_NEWS = "official_news"
    LAW = "law"
    SUBSIDY = "subsidy"
    FARMING_NEWS = "farming_news"
    RESEARCH = "research"
    MARKET = "market"


class SourceConfig(BaseModel):
    """Configuration for one scrapeable source.

    The scraper should not need to know where this source came from.
    It only receives validated source objects from the registry.
    """

    id: str = Field(min_length=3, pattern=r"^[a-z0-9_\-]+$")
    name: str = Field(min_length=2)
    kind: SourceKind
    url: HttpUrl
    homepage: HttpUrl | None = None

    jurisdiction: str = Field(
        min_length=2,
        description="Legal/policy scope, for example EU, NL, DE, BE, GLOBAL.",
    )
    country: str | None = Field(
        default=None,
        description="Main country when relevant. Use ISO-like short values such as NL, BE, DE, or EU.",
    )
    language: str = Field(default="en", pattern=r"^[a-z]{2}(-[A-Z]{2})?$")

    category: SourceCategory
    reliability: SourceReliability
    tags: list[str] = Field(default_factory=list)

    enabled: bool = True
    fetch_interval_minutes: int = Field(default=360, ge=15, le=10080)
    timeout_seconds: int = Field(default=20, ge=3, le=120)

    # Optional metadata for future scrapers.
    headers: dict[str, str] = Field(default_factory=dict)
    notes: str | None = None

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, tags: list[str]) -> list[str]:
        normalized = []
        for tag in tags:
            cleaned = tag.strip().lower().replace(" ", "-")
            if cleaned and cleaned not in normalized:
                normalized.append(cleaned)
        return normalized

    def scraper_options(self) -> dict[str, Any]:
        """Return only fields a scraper typically needs."""
        return {
            "id": self.id,
            "kind": self.kind.value,
            "url": str(self.url),
            "headers": self.headers,
            "timeout_seconds": self.timeout_seconds,
        }
