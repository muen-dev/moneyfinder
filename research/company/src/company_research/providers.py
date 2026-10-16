"""Thin clients for the scraping/search APIs and NY open-data hosts, recording every call for audit.

Only these fixed hosts are contacted directly. Company websites, BBB and anything else a page
mentions are fetched through Firecrawl or Nimble, never from this machine.
"""

import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx

from . import config

FIRECRAWL = "https://api.firecrawl.dev/v2"
TAVILY = "https://api.tavily.com"
NIMBLE = "https://sdk.nimbleway.com/v2"
SOCRATA_HOSTS = frozenset({"data.ny.gov", "data.cityofnewyork.us"})
USER_AGENT = "moneyfinder-company-research/0.1 (+https://github.com/NicholasSutin/moneyfinder)"


class ProviderError(RuntimeError):
    """An API call failed. The message never contains credentials."""


class MissingKey(ProviderError):
    pass


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass
class Call:
    """One API request and its response, kept on disk for audit."""

    provider: str
    endpoint: str
    request: dict
    fetched_at: str
    status: int | None = None
    response: Any = None
    error: str | None = None


@dataclass
class Recorder:
    calls: list[Call] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def add(self, call: Call) -> None:
        with self._lock:
            self.calls.append(call)

    def dump(self) -> list[dict]:
        with self._lock:
            return [asdict(c) for c in self.calls]


class Providers:
    """Firecrawl, Tavily, Nimble and Socrata calls. Collectors take this (or a test fake)."""

    def __init__(self, recorder: Recorder | None = None, timeout: float | None = None):
        self.recorder = recorder or Recorder()
        self._http = httpx.Client(
            timeout=timeout or config.HTTP_TIMEOUT, headers={"User-Agent": USER_AGENT}, follow_redirects=False
        )

    def close(self) -> None:
        self._http.close()

    def available(self, provider: str) -> bool:
        return config.api_key(f"{provider.upper()}_API_KEY") is not None

    # Firecrawl

    def firecrawl_map(self, url: str, limit: int = 200) -> list[dict]:
        body = {"url": url, "limit": limit, "includeSubdomains": False, "sitemap": "include"}
        data = self._post("firecrawl", f"{FIRECRAWL}/map", body)
        return [link if isinstance(link, dict) else {"url": link} for link in data.get("links") or []]

    def firecrawl_scrape(self, url: str, formats: list, only_main_content: bool = True) -> dict:
        body = {
            "url": url,
            "formats": formats,
            "onlyMainContent": only_main_content,
            "timeout": int(config.HTTP_TIMEOUT * 1000) - 5000,
            "blockAds": True,
        }
        data = self._post("firecrawl", f"{FIRECRAWL}/scrape", body)
        if not data.get("success", True) or "data" not in data:
            raise ProviderError(f"firecrawl scrape failed: {str(data.get('error'))[:200]}")
        return data["data"]

    # Tavily

    def tavily_search(
        self,
        query: str,
        include_domains: list[str] | None = None,
        topic: str = "general",
        max_results: int = 5,
        time_range: str | None = None,
    ) -> list[dict]:
        body: dict[str, Any] = {"query": query, "topic": topic, "max_results": max_results, "search_depth": "basic"}
        if include_domains:
            body["include_domains"] = include_domains
        if time_range:
            body["time_range"] = time_range
        if topic == "general":
            body["country"] = "united states"
        data = self._post("tavily", f"{TAVILY}/search", body)
        return [
            {
                "title": r.get("title") or "",
                "url": r.get("url") or "",
                "content": r.get("content") or "",
                "published_date": r.get("published_date"),
            }
            for r in data.get("results") or []
        ]

    # Nimble

    def nimble_search(self, query: str, include_domains: list[str] | None = None, max_results: int = 5) -> list[dict]:
        body: dict[str, Any] = {"query": query, "max_results": max_results, "search_depth": "lite"}
        if include_domains:
            body["include_domains"] = include_domains
        data = self._post("nimble", f"{NIMBLE}/search", body)
        return [
            {
                "title": r.get("title") or "",
                "url": r.get("url") or "",
                "content": r.get("description") or r.get("content") or "",
                "published_date": None,
            }
            for r in data.get("results") or []
        ]

    def nimble_extract(self, url: str) -> str:
        data = self._post("nimble", f"{NIMBLE}/extract", {"url": url, "render": True, "formats": ["markdown"]})
        if data.get("status") not in (None, "success"):
            raise ProviderError(f"nimble extract status {data.get('status')}")
        return (data.get("data") or {}).get("markdown") or ""

    # Search with fallback: Tavily first, Nimble if Tavily is unavailable or fails.

    def search(self, query: str, include_domains: list[str] | None = None, max_results: int = 5, **kw) -> tuple[list[dict], str]:
        errors, missing = [], 0
        for provider in ("tavily", "nimble"):
            if not self.available(provider):
                errors.append(f"{provider}: no API key")
                missing += 1
                continue
            try:
                if provider == "tavily":
                    return self.tavily_search(query, include_domains, max_results=max_results, **kw), "tavily"
                return self.nimble_search(query, include_domains, max_results=max_results), "nimble"
            except ProviderError as e:
                errors.append(str(e))
        raise (MissingKey if missing == 2 else ProviderError)("; ".join(errors))

    # Socrata open data (fixed public hosts, no key needed)

    def socrata(self, host: str, dataset: str, params: dict) -> list[dict]:
        if host not in SOCRATA_HOSTS:
            raise ProviderError(f"{host} is not an allowed open-data host")
        url = f"https://{host}/resource/{dataset}.json"
        headers = {}
        if token := config.setting("SOCRATA_APP_TOKEN"):
            headers["X-App-Token"] = token
        call = Call("socrata", url, dict(params), now())
        try:
            resp = self._http.get(url, params=params, headers=headers)
            if resp.status_code >= 500:  # these hosts return brief 503s under load; one retry
                time.sleep(2)
                resp = self._http.get(url, params=params, headers=headers)
            call.status = resp.status_code
            resp.raise_for_status()
            call.response = resp.json()
        except (httpx.HTTPError, ValueError) as e:
            call.error = _describe(e)
            raise ProviderError(f"{host}: {call.error}") from e
        finally:
            self.recorder.add(call)
        return call.response if isinstance(call.response, list) else []

    def _post(self, provider: str, url: str, body: dict) -> dict:
        key = config.api_key(f"{provider.upper()}_API_KEY")
        call = Call(provider, url, dict(body), now())
        if not key:
            call.error = "no API key"
            self.recorder.add(call)
            raise MissingKey(f"{provider}: no API key (set {provider.upper()}_API_KEY)")
        try:
            resp = self._http.post(url, json=body, headers={"Authorization": f"Bearer {key}"})
            call.status = resp.status_code
            try:
                call.response = resp.json()
            except ValueError:
                call.response = resp.text[:2000]
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            call.error = f"HTTP {e.response.status_code}: {_excerpt(call.response)}"
            raise ProviderError(f"{provider}: {call.error}") from e
        except httpx.HTTPError as e:
            call.error = _describe(e)
            raise ProviderError(f"{provider}: {call.error}") from e
        finally:
            self.recorder.add(call)
        return call.response if isinstance(call.response, dict) else {}


def _describe(e: Exception) -> str:
    if isinstance(e, httpx.HTTPStatusError):
        return f"HTTP {e.response.status_code}"
    if isinstance(e, httpx.TimeoutException):
        return "timed out"
    return type(e).__name__


def _excerpt(response: Any) -> str:
    if isinstance(response, dict):
        for key in ("error", "detail", "message"):
            if response.get(key):
                return str(response[key])[:200]
    return str(response)[:200]
