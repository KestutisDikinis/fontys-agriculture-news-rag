from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol

from app.scraper.models import ScrapeResult
from app.sources.schema import SourceConfig


class Fetcher(Protocol):
    """Network boundary used by scrapers.

    Tests can inject a fake fetcher. Production can use the default urllib
    implementation from app.scraper.http.
    """

    def __call__(self, url: str, *, timeout_seconds: int, headers: dict[str, str]) -> bytes:
        ...


class BaseScraper(ABC):
    @abstractmethod
    def scrape(self, source: SourceConfig) -> ScrapeResult:
        """Fetch and parse one configured source."""
