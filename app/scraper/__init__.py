from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .base import BaseScraper, Fetcher
from .http import FetchError, fetch_url
from .models import ScrapedArticle, ScrapeResult, ScrapeStatus
from .rss_scraper import RSSScraper


@dataclass(frozen=True)
class FeedItem:
    """
    Backward-compatible shape for the older ingestion/tests.

    Your real scraper now returns ScrapedArticle, but some existing code
    still expects FeedItem.
    """

    source_id: str
    title: str
    url: str
    summary: str = ""
    published_at: datetime | None = None
    raw: dict[str, Any] = field(default_factory=dict)


def _to_feed_item(article: ScrapedArticle) -> FeedItem:
    return FeedItem(
        source_id=article.source_id,
        title=article.title,
        url=str(article.url),
        summary=article.summary or article.content or "",
        published_at=article.published_at,
        raw=article.raw,
    )


def parse_feed_xml(source: Any, xml_text: str) -> list[FeedItem]:
    """
    Compatibility wrapper for older tests/code that call:

        parse_feed_xml(source, xml_text)

    Internally it uses the new RSSScraper.parse().
    """
    articles = RSSScraper().parse(xml_text, source)
    return [_to_feed_item(article) for article in articles]


def fetch_feed(source: Any, timeout: int = 15) -> str:
    """
    Compatibility wrapper for older code.

    Your new scraper normally uses RSSScraper.scrape(), but older code
    expects fetch_feed(source) -> str.
    """
    headers = getattr(source, "headers", {}) or {}

    payload = fetch_url(
        str(source.url),
        timeout_seconds=timeout,
        headers=headers,
    )

    return payload.decode("utf-8", errors="replace")


def scrape_source(source: Any, timeout: int = 15) -> list[FeedItem]:
    """
    Compatibility wrapper for older ingestion code.
    """
    xml_text = fetch_feed(source, timeout=timeout)
    return parse_feed_xml(source, xml_text)


def scrape_sources(
    sources: list[Any],
    timeout: int = 15,
) -> tuple[list[FeedItem], dict[str, str]]:
    """
    Compatibility wrapper for older ingestion code.

    Returns:
        items, errors
    """
    items: list[FeedItem] = []
    errors: dict[str, str] = {}

    for source in sources:
        try:
            items.extend(scrape_source(source, timeout=timeout))
        except Exception as exc:
            source_id = getattr(source, "id", "unknown")
            errors[source_id] = str(exc)

    return items, errors


__all__ = [
    "BaseScraper",
    "Fetcher",
    "FetchError",
    "RSSScraper",
    "ScrapedArticle",
    "ScrapeResult",
    "ScrapeStatus",
    "FeedItem",
    "fetch_url",
    "fetch_feed",
    "parse_feed_xml",
    "scrape_source",
    "scrape_sources",
]