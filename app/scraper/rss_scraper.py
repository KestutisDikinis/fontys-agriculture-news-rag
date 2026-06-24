from __future__ import annotations

import hashlib
import html
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Iterable

from app.scraper.base import BaseScraper, Fetcher
from app.scraper.http import fetch_url
from app.scraper.models import ScrapedArticle, ScrapeResult, ScrapeStatus
from app.sources.schema import SourceConfig, SourceKind

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")

NAMESPACES = {
    "atom": "http://www.w3.org/2005/Atom",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
}


class RSSScraper(BaseScraper):
    """Scraper for RSS 2.0 and Atom feeds."""

    def __init__(self, fetcher: Fetcher = fetch_url) -> None:
        self._fetcher = fetcher

    def scrape(self, source: SourceConfig) -> ScrapeResult:
        if source.kind != SourceKind.RSS:
            return ScrapeResult(
                source_id=source.id,
                status=ScrapeStatus.SKIPPED,
                error=f"RSSScraper only supports rss sources, got {source.kind.value}",
            )

        try:
            payload = self._fetcher(
                str(source.url),
                timeout_seconds=source.timeout_seconds,
                headers=source.headers,
            )
            articles = self.parse(payload, source)
            return ScrapeResult(
                source_id=source.id,
                status=ScrapeStatus.SUCCESS,
                articles=articles,
            )
        except Exception as exc:  # keep scrape loop alive; caller can inspect error
            return ScrapeResult(
                source_id=source.id,
                status=ScrapeStatus.FAILED,
                error=str(exc),
            )

    def parse(self, payload: bytes | str, source: SourceConfig) -> list[ScrapedArticle]:
        xml_payload = payload.decode("utf-8", errors="replace") if isinstance(payload, bytes) else payload
        root = ET.fromstring(xml_payload)

        if self._is_atom(root):
            return list(self._parse_atom(root, source))
        return list(self._parse_rss(root, source))

    def _parse_rss(self, root: ET.Element, source: SourceConfig) -> Iterable[ScrapedArticle]:
        channel = root.find("channel")
        if channel is None:
            return []

        for item in channel.findall("item"):
            title = _clean_text(_child_text(item, "title"))
            url = _clean_text(_child_text(item, "link"))
            if not title or not url:
                continue

            published_at = _parse_datetime(
                _child_text(item, "pubDate")
                or _child_text(item, "published")
                or _child_text(item, "updated")
            )
            description = _clean_html(_child_text(item, "description"))
            content = _clean_html(_child_text(item, "content:encoded") or description)
            guid = _clean_text(_child_text(item, "guid"))
            author = _clean_text(_child_text(item, "author") or _child_text(item, "dc:creator")) or None

            yield ScrapedArticle(
                id=_stable_article_id(source.id, guid or url or title),
                source_id=source.id,
                title=title,
                url=url,
                published_at=published_at,
                author=author,
                summary=description or None,
                content=content or None,
                raw={
                    "guid": guid,
                    "feed_type": "rss",
                    "source_name": source.name,
                },
            )

    def _parse_atom(self, root: ET.Element, source: SourceConfig) -> Iterable[ScrapedArticle]:
        for entry in root.findall("atom:entry", NAMESPACES):
            title = _clean_text(_child_text(entry, "atom:title"))
            url = _atom_link(entry)
            if not title or not url:
                continue

            published_at = _parse_datetime(
                _child_text(entry, "atom:published") or _child_text(entry, "atom:updated")
            )
            summary = _clean_html(_child_text(entry, "atom:summary"))
            content = _clean_html(_child_text(entry, "atom:content") or summary)
            entry_id = _clean_text(_child_text(entry, "atom:id"))
            author = _atom_author(entry)

            yield ScrapedArticle(
                id=_stable_article_id(source.id, entry_id or url or title),
                source_id=source.id,
                title=title,
                url=url,
                published_at=published_at,
                author=author,
                summary=summary or None,
                content=content or None,
                raw={
                    "entry_id": entry_id,
                    "feed_type": "atom",
                    "source_name": source.name,
                },
            )

    @staticmethod
    def _is_atom(root: ET.Element) -> bool:
        return root.tag == f"{{{NAMESPACES['atom']}}}feed" or root.tag == "feed"


def _stable_article_id(source_id: str, unique_value: str) -> str:
    digest = hashlib.sha256(f"{source_id}:{unique_value}".encode("utf-8")).hexdigest()
    return digest[:32]


def _child_text(parent: ET.Element, path: str) -> str | None:
    if ":" in path:
        prefix, local_name = path.split(":", 1)
        namespace = NAMESPACES.get(prefix)
        if namespace:
            child = parent.find(f"{{{namespace}}}{local_name}")
        else:
            child = parent.find(path)
    else:
        child = parent.find(path)

    if child is None:
        return None
    return "".join(child.itertext())


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    return _WHITESPACE_RE.sub(" ", html.unescape(value)).strip()


def _clean_html(value: str | None) -> str:
    if not value:
        return ""
    unescaped = html.unescape(value)
    without_tags = _HTML_TAG_RE.sub(" ", unescaped)
    return _clean_text(without_tags)


def _parse_datetime(value: str | None) -> datetime | None:
    value = _clean_text(value)
    if not value:
        return None

    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    except (TypeError, ValueError):
        pass

    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return None


def _atom_link(entry: ET.Element) -> str:
    for link in entry.findall("atom:link", NAMESPACES):
        rel = link.attrib.get("rel", "alternate")
        href = link.attrib.get("href")
        if href and rel == "alternate":
            return _clean_text(href)

    first = entry.find("atom:link", NAMESPACES)
    if first is not None:
        return _clean_text(first.attrib.get("href"))
    return ""


def _atom_author(entry: ET.Element) -> str | None:
    author = entry.find("atom:author", NAMESPACES)
    if author is None:
        return None
    return _clean_text(_child_text(author, "atom:name")) or None
