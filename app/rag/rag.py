from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from app.classification import (
    CURRENT_OR_RECENT,
    RUMOR,
    UPCOMING_THIS_MONTH,
    UPCOMING_WITHIN_YEAR,
)
from app.config import settings
from app.db import SQLiteStore
from app.llm import LLMClient
from app.rag.chunker import chunk_text
from app.rag.embedder import HashingEmbedder, cosine_similarity


FUTURE_QUERY_TERMS = {
    "future",
    "near future",
    "upcoming",
    "coming",
    "soon",
    "next",
    "this month",
    "next month",
    "this year",
    "deadline",
    "deadlines",
    "change",
    "changes",
    "new law",
    "new laws",
    "new rule",
    "new rules",
    "will happen",
    "going to happen",
    "planned",
    "proposal",
    "proposed",
    "consultation",
}

LAW_QUERY_TERMS = {
    "law",
    "laws",
    "rule",
    "rules",
    "regulation",
    "regulations",
    "policy",
    "policies",
    "compliance",
    "subsidy",
    "grant",
    "scheme",
    "ban",
    "inspection",
    "deadline",
}


@dataclass(frozen=True)
class SearchResult:
    article_id: int
    title: str
    url: str
    category: str
    source_id: str
    chunk_index: int
    text: str
    score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "article_id": self.article_id,
            "title": self.title,
            "url": self.url,
            "category": self.category,
            "source_id": self.source_id,
            "chunk_index": self.chunk_index,
            "text": self.text,
            "score": round(self.score, 4),
        }


class LocalRAG:
    def __init__(self, db_path: str | Path | None = None):
        self.store = SQLiteStore(db_path or settings.database_path)
        self.embedder = HashingEmbedder()
        self.llm = LLMClient()

    def rebuild_index(self) -> dict[str, int]:
        articles = self.store.list_articles(limit=10_000)
        indexed_articles = 0
        indexed_chunks = 0

        for article in articles:
            if article.id is None:
                continue

            text = article.searchable_text
            chunks = chunk_text(text)

            embedded_chunks = [
                (index, chunk, self.embedder.embed(chunk))
                for index, chunk in enumerate(chunks)
            ]

            self.store.replace_chunks(article.id, embedded_chunks)

            indexed_articles += 1
            indexed_chunks += len(embedded_chunks)

        return {
            "articles": indexed_articles,
            "chunks": indexed_chunks,
        }

    def search(
        self,
        query: str,
        *,
        top_k: int | None = None,
        categories: set[str] | None = None,
    ) -> list[SearchResult]:
        top_k = top_k or settings.rag_top_k

        if categories is None:
            categories = _infer_categories_from_query(query)

        query_embedding = self.embedder.embed(query)
        results: list[SearchResult] = []

        for row in self.store.list_chunks():
            category = str(row["category"])

            if categories and category not in categories:
                continue

            embedding = json.loads(row["embedding_json"])
            score = cosine_similarity(query_embedding, embedding)

            results.append(
                SearchResult(
                    article_id=int(row["article_id"]),
                    title=row["title"],
                    url=row["url"],
                    category=category,
                    source_id=row["source_id"],
                    chunk_index=int(row["chunk_index"]),
                    text=row["text"],
                    score=score,
                )
            )

        return sorted(results, key=lambda item: item.score, reverse=True)[:top_k]

    def answer(
        self,
        query: str,
        *,
        top_k: int | None = None,
    ) -> dict[str, Any]:
        categories = _infer_categories_from_query(query)

        matches = self.search(
            query,
            top_k=top_k,
            categories=categories,
        )

        if not matches:
            return {
                "answer": _empty_answer(query, categories),
                "answer_mode": "no_matches",
                "matches": [],
                "sources": [],
            }

        answer_context = "\n\n---\n\n".join(
            (
                f"Title: {match.title}\n"
                f"Category: {match.category}\n"
                f"Source: {match.source_id}\n"
                f"URL: {match.url}\n"
                f"Content: {match.text}"
            )
            for match in matches
        )

        answer = self.llm.answer_from_context(
            question=query,
            context=answer_context,
        )

        return {
            "answer": answer,
            "answer_mode": "local_llm",
            "matches": [match.to_dict() for match in matches],
            "sources": _unique_sources(matches),
        }


def _infer_categories_from_query(query: str) -> set[str] | None:
    q = query.lower()

    if any(term in q for term in FUTURE_QUERY_TERMS):
        return {
            UPCOMING_THIS_MONTH,
            UPCOMING_WITHIN_YEAR,
            RUMOR,
        }

    if any(term in q for term in LAW_QUERY_TERMS):
        return {
            UPCOMING_THIS_MONTH,
            UPCOMING_WITHIN_YEAR,
            RUMOR,
            CURRENT_OR_RECENT,
        }

    return None


def _empty_answer(query: str, categories: set[str] | None) -> str:
    if categories:
        return (
            "I could not find any indexed agriculture items classified as upcoming, "
            "near-future, or proposal/rumor items. The system should not answer this "
            "question using background_news articles, because that would make ordinary "
            "news look like future changes."
        )

    return "I could not find relevant information in the indexed agriculture sources."


def _future_or_policy_answer(matches: list[SearchResult]) -> str:
    lines = [
        "I found these relevant future-looking or policy-related items in the indexed sources:"
    ]

    for match in matches:
        lines.append(
            f"- {match.title} [{match.category}]: {match.text}"
        )

    return "\n".join(lines)


def _unique_sources(matches: list[SearchResult]) -> list[dict[str, str]]:
    seen: set[str] = set()
    sources: list[dict[str, str]] = []

    for match in matches:
        if match.url in seen:
            continue

        seen.add(match.url)

        sources.append(
            {
                "title": match.title,
                "url": match.url,
                "category": match.category,
                "source_id": match.source_id,
            }
        )

    return sources