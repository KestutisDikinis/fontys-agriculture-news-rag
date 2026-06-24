from __future__ import annotations

from app.scraper.http import fetch_url
from app.sources import get_sources


def main() -> None:
    for source in get_sources():
        print(f"\nChecking {source.id}")
        print(source.url)

        try:
            payload = fetch_url(
                source.url,
                timeout_seconds=source.timeout_seconds,
                headers=source.headers,
            )
            print(f"OK: {len(payload):,} bytes")
            print(payload[:120].decode("utf-8", errors="replace"))
        except Exception as exc:
            print(f"FAILED: {exc}")


if __name__ == "__main__":
    main()