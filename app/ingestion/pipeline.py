from __future__ import annotations

from dataclasses import dataclass, field

from app.classification import classify_text
from app.config import settings
from app.db import Article, SQLiteStore
from app.rag import LocalRAG
from app.scraper import FeedItem, scrape_sources
from app.sources import Source, get_sources


@dataclass(frozen=True)
class IngestionReport:
    scraped: int
    saved: int
    indexed_articles: int
    indexed_chunks: int
    errors: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "scraped": self.scraped,
            "saved": self.saved,
            "indexed_articles": self.indexed_articles,
            "indexed_chunks": self.indexed_chunks,
            "errors": self.errors,
        }


class IngestionPipeline:
    def __init__(self, store: SQLiteStore | None = None):
        settings.ensure_dirs()
        self.store = store or SQLiteStore(settings.database_path)

    def run(
        self,
        *,
        source_ids: list[str] | None = None,
        limit_per_source: int = 20,
        rebuild_rag: bool = True,
    ) -> IngestionReport:
        sources = get_sources(source_ids)
        items, errors = scrape_sources(sources, timeout=settings.rss_timeout_seconds)

        saved = 0
        per_source_count: dict[str, int] = {}
        for item in items:
            count = per_source_count.get(item.source_id, 0)
            if count >= limit_per_source:
                continue
            per_source_count[item.source_id] = count + 1
            self.save_feed_item(item)
            saved += 1

        index_stats = {"articles": 0, "chunks": 0}
        if rebuild_rag:
            index_stats = LocalRAG(settings.database_path).rebuild_index()

        return IngestionReport(
            scraped=len(items),
            saved=saved,
            indexed_articles=index_stats["articles"],
            indexed_chunks=index_stats["chunks"],
            errors=errors,
        )

    def run_for_sources(self, sources: list[Source], *, limit_per_source: int = 20) -> IngestionReport:
        items, errors = scrape_sources(sources, timeout=settings.rss_timeout_seconds)
        saved = 0
        per_source_count: dict[str, int] = {}
        for item in items:
            count = per_source_count.get(item.source_id, 0)
            if count >= limit_per_source:
                continue
            per_source_count[item.source_id] = count + 1
            self.save_feed_item(item)
            saved += 1
        index_stats = LocalRAG(settings.database_path).rebuild_index()
        return IngestionReport(len(items), saved, index_stats["articles"], index_stats["chunks"], errors)

    def save_feed_item(self, item: FeedItem) -> int:
        classification = classify_text(item.title, item.summary)
        article = Article(
            source_id=item.source_id,
            title=item.title or "Untitled",
            url=item.url,
            summary=item.summary,
            content=item.summary,
            published_at=item.published_at,
            category=classification.category,
            confidence=classification.confidence,
            effective_date=classification.effective_date,
            impact_level=classification.impact_level,
        )
        return self.store.upsert_article(article)
