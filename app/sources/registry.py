from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from .schema import SourceKind


@dataclass(frozen=True)
class Source:
    id: str
    name: str
    url: str
    region: str
    kind: SourceKind = SourceKind.RSS
    reliability: str = "official"
    enabled: bool = True
    timeout_seconds: int = 45
    headers: dict[str, str] = field(default_factory=dict)


DEFAULT_SOURCES: tuple[Source, ...] = (
    Source(
        id="eu_agriculture_news",
        name="European Commission Agriculture News",
        url="https://ec.europa.eu/newsroom/agri/feed?item_type_id=994&lang=en&orderby=item_date",
        region="EU",
        timeout_seconds=45,
    ),
    Source(
        id="eu_agriculture_consultations",
        name="European Commission Agriculture Consultations",
        url="https://ec.europa.eu/newsroom/agri/feed?item_type_id=1000&lang=en&orderby=item_date",
        region="EU",
        timeout_seconds=45,
    ),
    Source(
        id="eu_agriculture_calls",
        name="European Commission Agriculture Calls",
        url="https://ec.europa.eu/newsroom/agri/feed?item_type_id=1004&lang=en&orderby=item_date",
        region="EU",
        timeout_seconds=45,
    ),
    Source(
        id="uk_defra_news",
        name="UK DEFRA News and Communications",
        url=(
            "https://www.gov.uk/search/news-and-communications.atom?"
            "organisations%5B%5D=department-for-environment-food-rural-affairs"
        ),
        region="UK",
        timeout_seconds=45,
    ),
    Source(
        id="usda_latest_news",
        name="USDA Latest News",
        url="https://www.usda.gov/rss/latest-releases.xml",
        region="US",
        timeout_seconds=60,
    ),
)


def get_sources(source_ids: Iterable[str] | None = None) -> list[Source]:
    wanted = set(source_ids or [])

    return [
        source
        for source in DEFAULT_SOURCES
        if source.enabled and (not wanted or source.id in wanted)
    ]


def get_source(source_id: str) -> Source | None:
    for source in DEFAULT_SOURCES:
        if source.id == source_id:
            return source

    return None