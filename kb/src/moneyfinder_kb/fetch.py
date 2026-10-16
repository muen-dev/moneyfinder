"""Fetch a URL: original bytes over plain HTTP, plus Firecrawl markdown for HTML when configured."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

USER_AGENT = "Mozilla/5.0 (compatible; moneyfinder-kb/0.1)"
FIRECRAWL_SCRAPE = "https://api.firecrawl.dev/v2/scrape"


@dataclass
class Fetched:
    url: str
    status: int
    content_type: str
    body: bytes
    markdown: str | None = None
    title: str | None = None
    via: str = "http"


def fetch(url: str, firecrawl_api_key: str | None = None, timeout: float = 60) -> Fetched:
    with httpx.Client(follow_redirects=True, timeout=timeout, headers={"User-Agent": USER_AGENT}) as client:
        resp = client.get(url)
        resp.raise_for_status()
    content_type = resp.headers.get("content-type", "application/octet-stream").split(";")[0].strip().lower()
    fetched = Fetched(url=str(resp.url), status=resp.status_code, content_type=content_type, body=resp.content)
    if firecrawl_api_key and content_type == "text/html":
        try:
            fetched.markdown, fetched.title = _firecrawl_markdown(url, firecrawl_api_key, timeout)
            fetched.via = "http+firecrawl"
        except (httpx.HTTPError, KeyError, ValueError):
            pass  # fall back to the built-in HTML extractor
    return fetched


def _firecrawl_markdown(url: str, api_key: str, timeout: float) -> tuple[str, str | None]:
    resp = httpx.post(
        FIRECRAWL_SCRAPE,
        headers={"Authorization": f"Bearer {api_key}"},
        json={"url": url, "formats": ["markdown"], "onlyMainContent": True},
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()["data"]
    title = data.get("metadata", {}).get("title")
    if isinstance(title, list):
        title = title[0] if title else None
    return data.get("markdown") or "", title
