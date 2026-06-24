from __future__ import annotations

from app.ingestion import IngestionPipeline


if __name__ == "__main__":
    report = IngestionPipeline().run(limit_per_source=20, rebuild_rag=True)
    print(report.to_dict())
