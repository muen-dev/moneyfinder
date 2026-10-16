"""Network access: official government pages, NY open data, and search APIs, with every call recorded.

Pages are only fetched from government hosts (config.OFFICIAL_*), over https, honoring robots.txt.
A redirect is followed only when its target is also official. Hosts that block direct requests are
read through Firecrawl instead. Search results are recorded as candidates and never fetched here.
"""

import threading
import time
import urllib.robotparser
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx

from . import config

FIRECRAWL = "https://api.firecrawl.dev/v2"
TAVILY = "https://api.tavily.com"
NIMBLE = "https://sdk.nimbleway.com/v2"
SOCRATA_HOSTS = frozenset({"data.ny.gov", "data.cityofnewyork.us"})
USER_AGENT = "moneyfinder-legal-research/0.1 (+https://github.com/NicholasSutin/moneyfinder)"


class ProviderError(RuntimeError):
    """A request failed. The message never contains credentials."""


class MissingKey(ProviderError):
    pass


class NotAllowed(ProviderError):
    """The URL is not on an official host, or robots.txt disallows it."""


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def official_url(url: str) -> str | None:
    """The https form of url if it is on an official host, else None. Drops fragments."""
    parts = urlsplit(url.strip())
    host = (parts.hostname or "").lower()
    if parts.scheme not in ("http", "https") or parts.username or parts.password or parts.port not in (None, 80, 443):
        return None
    if not (host in config.OFFICIAL_HOSTS or host.endswith(config.OFFICIAL_SUFFIXES)):
        return None
    return urlunsplit(("https", host, parts.path or "/", parts.query, ""))


@dataclass
class Call:
    provider: str
    url: str
    fetched_at: str
    status: int | None = None
    error: str | None = None
    detail: dict = field(default_factory=dict)


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


@dataclass
class Page:
    url: str  # as requested
    final_url: str
    status: int
    content_type: str
    html: str
    via: str  # "direct" | "firecrawl"
    fetched_at: str


class Providers:
    """Official pages, Socrata and search. The pipeline takes this (or a test fake)."""

    def __init__(self, recorder: Recorder | None = None, timeout: float | None = None, delay: float | None = None):
        self.recorder = recorder or Recorder()
        self.delay = config.REQUEST_DELAY if delay is None else delay
        self._http = httpx.Client(
            timeout=timeout or config.HTTP_TIMEOUT, headers={"User-Agent": USER_AGENT}, follow_redirects=False
        )
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        self._last_hit: dict[str, float] = {}

    def close(self) -> None:
        self._http.close()

    def available(self, provider: str) -> bool:
        return config.api_key(f"{provider.upper()}_API_KEY") is not None

    # Official pages

    def page(self, url: str) -> Page:
        start = official_url(url)
        if not start:
            raise NotAllowed(f"not an official host: {urlsplit(url).hostname}")
        host = urlsplit(start).hostname
        if host in config.SCRAPER_ONLY_HOSTS:
            return self._firecrawl_page(start)
        try:
            return self._direct_page(start)
        except ProviderError as e:
            if "HTTP 403" in str(e) and self.available("firecrawl"):
                return self._firecrawl_page(start)
            raise

    def _direct_page(self, url: str) -> Page:
        current = url
        for _ in range(config.MAX_REDIRECTS + 1):
            if not self._robots_allow(current):
                raise NotAllowed(f"robots.txt disallows {urlsplit(current).path}")
            call = Call("direct", current, now())
            try:
                self._pace(urlsplit(current).hostname or "")
                resp = self._http.get(current)
                call.status = resp.status_code
                if resp.is_redirect:
                    target = official_url(urljoin(current, resp.headers.get("location", "")))
                    call.detail["redirect"] = target
                    if not target:
                        call.error = "redirect to a non-official host"
                        raise NotAllowed(call.error)
                    current = target
                    continue
                if resp.status_code >= 400:
                    call.error = f"HTTP {resp.status_code}"
                    raise ProviderError(f"{urlsplit(current).hostname}: {call.error}")
                content_type = resp.headers.get("content-type", "").split(";")[0].strip()
                call.detail["content_type"] = content_type
                if len(resp.content) > config.MAX_PAGE_BYTES:
                    call.error = "page too large"
                    raise ProviderError(call.error)
                return Page(url, current, resp.status_code, content_type, resp.text, "direct", call.fetched_at)
            except httpx.HTTPError as e:
                call.error = _describe(e)
                raise ProviderError(f"{urlsplit(current).hostname}: {call.error}") from e
            finally:
                self.recorder.add(call)
        raise ProviderError("too many redirects")

    def _firecrawl_page(self, url: str) -> Page:
        body = {"url": url, "formats": ["rawHtml"], "onlyMainContent": False, "timeout": int(config.HTTP_TIMEOUT * 1000)}
        data = self._post("firecrawl", f"{FIRECRAWL}/scrape", body)
        page = data.get("data") or {}
        final = official_url((page.get("metadata") or {}).get("sourceURL") or url) or url
        return Page(url, final, 200, "text/html", page.get("rawHtml") or "", "firecrawl", now())

    def _robots_allow(self, url: str) -> bool:
        parts = urlsplit(url)
        host = parts.hostname or ""
        if host not in self._robots:
            parser = urllib.robotparser.RobotFileParser()
            try:
                self._pace(host)
                resp = self._http.get(f"https://{host}/robots.txt")
                if resp.status_code == 200:
                    parser.parse(resp.text.splitlines())
                    self._robots[host] = parser
                else:
                    self._robots[host] = None  # no robots.txt: allowed
            except httpx.HTTPError:
                self._robots[host] = None
        parser = self._robots[host]
        return parser is None or parser.can_fetch(USER_AGENT, url)

    def _pace(self, host: str) -> None:
        wait = self._last_hit.get(host, 0) + self.delay - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self._last_hit[host] = time.monotonic()

    # NY open data (fixed public hosts, no key needed)

    def socrata(self, host: str, dataset: str, params: dict) -> list[dict]:
        if host not in SOCRATA_HOSTS:
            raise NotAllowed(f"{host} is not an allowed open-data host")
        url = f"https://{host}/resource/{dataset}.json"
        headers = {}
        if token := config.setting("SOCRATA_APP_TOKEN"):
            headers["X-App-Token"] = token
        call = Call("socrata", url, now(), detail={"params": dict(params)})
        try:
            resp = self._http.get(url, params=params, headers=headers)
            if resp.status_code >= 500:  # these hosts return brief 503s under load; one retry
                time.sleep(2)
                resp = self._http.get(url, params=params, headers=headers)
            call.status = resp.status_code
            resp.raise_for_status()
            rows = resp.json()
        except (httpx.HTTPError, ValueError) as e:
            call.error = _describe(e)
            raise ProviderError(f"{host}: {call.error}") from e
        finally:
            self.recorder.add(call)
        return rows if isinstance(rows, list) else []

    # Search: Tavily first, Nimble if Tavily is unavailable or fails. Results are leads, not facts.

    def search(self, query: str, include_domains: list[str], max_results: int = 8) -> tuple[list[dict], str]:
        errors, missing = [], 0
        for provider in ("tavily", "nimble"):
            if not self.available(provider):
                errors.append(f"{provider}: no API key")
                missing += 1
                continue
            try:
                if provider == "tavily":
                    body = {"query": query, "include_domains": include_domains, "max_results": max_results,
                            "search_depth": "basic", "topic": "general", "country": "united states"}
                    data = self._post("tavily", f"{TAVILY}/search", body)
                    results = [{"title": r.get("title") or "", "url": r.get("url") or "", "content": r.get("content") or ""}
                               for r in data.get("results") or []]
                else:
                    body = {"query": query, "include_domains": include_domains, "max_results": max_results, "search_depth": "lite"}
                    data = self._post("nimble", f"{NIMBLE}/search", body)
                    results = [{"title": r.get("title") or "", "url": r.get("url") or "",
                                "content": r.get("description") or r.get("content") or ""}
                               for r in data.get("results") or []]
                return results, provider
            except ProviderError as e:
                errors.append(str(e))
        raise (MissingKey if missing == 2 else ProviderError)("; ".join(errors))

    def _post(self, provider: str, url: str, body: dict) -> dict:
        key = config.api_key(f"{provider.upper()}_API_KEY")
        call = Call(provider, url, now(), detail={"request": dict(body)})  # the key travels in a header, never here
        if not key:
            call.error = "no API key"
            self.recorder.add(call)
            raise MissingKey(f"{provider}: no API key (set {provider.upper()}_API_KEY)")
        try:
            resp = self._http.post(url, json=body, headers={"Authorization": f"Bearer {key}"})
            call.status = resp.status_code
            try:
                data = resp.json()
            except ValueError:
                data = {"error": resp.text[:200]}
            if resp.status_code >= 400:
                call.error = f"HTTP {resp.status_code}: {_excerpt(data)}"
                raise ProviderError(f"{provider}: {call.error}")
        except httpx.HTTPError as e:
            call.error = _describe(e)
            raise ProviderError(f"{provider}: {call.error}") from e
        finally:
            self.recorder.add(call)
        return data if isinstance(data, dict) else {}


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
