from __future__ import annotations

from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class FetchError(RuntimeError):
    """Raised when fetching a source fails."""


def fetch_url(url: str, *, timeout_seconds: int, headers: dict[str, str]) -> bytes:
    request_headers = {
        "User-Agent": "AgriWatchBot/0.1 (+https://example.local/agri-watch)",
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
        **headers,
    }
    request = Request(url, headers=request_headers)

    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - configured trusted sources only
            return response.read()
    except HTTPError as exc:
        raise FetchError(f"HTTP {exc.code} while fetching {url}") from exc
    except URLError as exc:
        reason = getattr(exc, "reason", exc)
        raise FetchError(f"Network error while fetching {url}: {reason}") from exc
    except TimeoutError as exc:
        raise FetchError(f"Timeout while fetching {url}") from exc
