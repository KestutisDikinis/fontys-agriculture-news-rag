from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Iterator

from app.db.models import Article


def _dt_to_str(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _date_to_str(value: date | None) -> str | None:
    return value.isoformat() if value else None


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


class SQLiteStore:
    """Small SQLite repository for articles and vector chunks."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_schema()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL UNIQUE,
                    summary TEXT NOT NULL DEFAULT '',
                    content TEXT NOT NULL DEFAULT '',
                    published_at TEXT,
                    category TEXT NOT NULL DEFAULT 'background_news',
                    confidence REAL NOT NULL DEFAULT 0,
                    effective_date TEXT,
                    impact_level TEXT NOT NULL DEFAULT 'medium',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    article_id INTEGER NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    embedding_json TEXT NOT NULL,
                    FOREIGN KEY(article_id) REFERENCES articles(id) ON DELETE CASCADE,
                    UNIQUE(article_id, chunk_index)
                );

                CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category);
                CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source_id);
                CREATE INDEX IF NOT EXISTS idx_chunks_article ON chunks(article_id);
                """
            )

    def upsert_article(self, article: Article) -> int:
        created = article.created_at or datetime.now(timezone.utc)
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO articles (
                    source_id, title, url, summary, content, published_at,
                    category, confidence, effective_date, impact_level, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    source_id=excluded.source_id,
                    title=excluded.title,
                    summary=excluded.summary,
                    content=excluded.content,
                    published_at=excluded.published_at,
                    category=excluded.category,
                    confidence=excluded.confidence,
                    effective_date=excluded.effective_date,
                    impact_level=excluded.impact_level
                """,
                (
                    article.source_id,
                    article.title,
                    article.url,
                    article.summary,
                    article.content,
                    _dt_to_str(article.published_at),
                    article.category,
                    article.confidence,
                    _date_to_str(article.effective_date),
                    article.impact_level,
                    _dt_to_str(created),
                ),
            )
            row = conn.execute("SELECT id FROM articles WHERE url = ?", (article.url,)).fetchone()
            return int(row["id"])

    def list_articles(
        self,
        *,
        category: str | None = None,
        source_id: str | None = None,
        search: str | None = None,
        limit: int = 50,
    ) -> list[Article]:
        query = "SELECT * FROM articles WHERE 1=1"
        params: list[object] = []
        if category:
            query += " AND category = ?"
            params.append(category)
        if source_id:
            query += " AND source_id = ?"
            params.append(source_id)
        if search:
            query += " AND (LOWER(title) LIKE ? OR LOWER(summary) LIKE ? OR LOWER(content) LIKE ?)"
            needle = f"%{search.lower()}%"
            params.extend([needle, needle, needle])
        query += " ORDER BY COALESCE(published_at, created_at) DESC LIMIT ?"
        params.append(limit)

        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._article_from_row(row) for row in rows]

    def get_article(self, article_id: int) -> Article | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
        return self._article_from_row(row) if row else None

    def delete_all_chunks(self) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM chunks")

    def replace_chunks(self, article_id: int, chunks: list[tuple[int, str, list[float]]]) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM chunks WHERE article_id = ?", (article_id,))
            conn.executemany(
                """
                INSERT INTO chunks(article_id, chunk_index, text, embedding_json)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (article_id, chunk_index, text, json.dumps(embedding))
                    for chunk_index, text, embedding in chunks
                ],
            )

    def list_chunks(self) -> list[sqlite3.Row]:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT chunks.*, articles.title, articles.url, articles.category, articles.source_id
                FROM chunks
                JOIN articles ON articles.id = chunks.article_id
                """
            ).fetchall()

    @staticmethod
    def _article_from_row(row: sqlite3.Row) -> Article:
        return Article(
            id=int(row["id"]),
            source_id=row["source_id"],
            title=row["title"],
            url=row["url"],
            summary=row["summary"] or "",
            content=row["content"] or "",
            published_at=_parse_dt(row["published_at"]),
            category=row["category"],
            confidence=float(row["confidence"]),
            effective_date=_parse_date(row["effective_date"]),
            impact_level=row["impact_level"],
            created_at=_parse_dt(row["created_at"]),
        )
