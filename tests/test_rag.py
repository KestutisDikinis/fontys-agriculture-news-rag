from pathlib import Path

from app.db import Article, SQLiteStore
from app.rag import LocalRAG


def test_rag_indexes_and_searches(tmp_path: Path):
    db_path = tmp_path / "test.sqlite3"
    store = SQLiteStore(db_path)
    store.upsert_article(
        Article(
            source_id="test",
            title="New water rule",
            url="https://example.test/water",
            summary="Farmers must keep records for irrigation water use from 2026-04-01.",
            category="upcoming_within_year",
        )
    )

    rag = LocalRAG(db_path)
    stats = rag.rebuild_index()
    assert stats["articles"] == 1
    results = rag.search("irrigation water records", top_k=1)
    assert len(results) == 1
    assert "irrigation" in results[0].text.lower()
