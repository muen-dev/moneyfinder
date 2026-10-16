"""Fetch → lake → extract → chunk → embed → SurrealDB, plus a polite same-site crawler."""

from __future__ import annotations

import re
import time
from collections import deque
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from urllib.parse import urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import httpx
from surrealdb import RecordID

from .chunk import chunk_pages
from .db import without_none
from .extract import extract
from .fetch import USER_AGENT, fetch
from .lake import put_raw, sha256, text_key

if TYPE_CHECKING:
    from .kb import KB

INSERT_BATCH = 200


@dataclass
class SourceSpec:
    url: str
    authority: str = "unknown"
    jurisdiction: str | None = None
    agency: str | None = None
    tags: list[str] = field(default_factory=list)
    follow: list[str] = field(default_factory=list)  # regexes; matching links are recorded and crawled
    depth: int = 0


@dataclass
class IngestResult:
    url: str
    status: str  # "new" | "unchanged" | "skipped" | "failed"
    chunks: int = 0
    links: list[tuple[str, str]] = field(default_factory=list)
    error: str | None = None


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", parts.query, ""))


def classify_authority(url: str, default: str) -> str:
    """Best-effort authority from URL shape. Extend as new sources are added."""
    path = urlsplit(url).path.lower()
    if "/current_forms/" in path or re.search(r"/forms?/.*\.pdf$", path):
        return "form_instructions" if re.search(r"i\.pdf$", path) else "form"
    return default


def ingest_url(kb: KB, spec: SourceSpec, force: bool = False) -> IngestResult:
    url = normalize_url(spec.url)
    src = RecordID("source", url)
    _upsert_source(kb, src, url, spec)
    try:
        fetched = fetch(url, kb.settings.firecrawl_api_key)
        extracted = extract(fetched)
    except Exception as e:  # network, HTTP status, unparseable content
        kb.db.run("UPDATE $src SET last_error = $err;", {"src": src, "err": f"{type(e).__name__}: {e}"[:500]})
        return IngestResult(url, "failed", error=str(e))

    raw = put_raw(
        kb.lake,
        fetched.body,
        fetched.content_type,
        {
            "url": url,
            "final_url": fetched.url,
            "status": fetched.status,
            "content_type": fetched.content_type,
            "via": fetched.via,
            "fetched_at": datetime.now(UTC).isoformat(),
        },
    )
    text = extracted.markdown()
    digest = sha256(text.encode())
    doc = RecordID("document", digest)

    chunk_count = 0
    is_new = force or not kb.db.one("RETURN record::exists($doc);", {"doc": doc})
    if is_new:
        kb.lake.put(text_key(digest), text.encode(), "text/markdown")
        chunks = chunk_pages(extracted.pages)
        vectors = kb.embedder.embed([c.text for c in chunks]) if kb.embedder and chunks else None
        rows = [
            {
                "id": RecordID("chunk", [digest, c.ordinal]),
                "document": doc,
                "ordinal": c.ordinal,
                "text": c.text,
                **({"heading": c.heading} if c.heading else {}),
                **({"page": c.page} if c.page is not None else {}),
                **({"embedding": vectors[i]} if vectors else {}),
            }
            for i, c in enumerate(chunks)
        ]
        # Clear leftovers from an interrupted run, insert chunks, then write the document
        # last: its existence marks the chunks as complete.
        kb.db.run("DELETE chunk WHERE document = $doc;", {"doc": doc})
        for i in range(0, len(rows), INSERT_BATCH):
            kb.db.run("INSERT INTO chunk $rows RETURN NONE;", {"rows": rows[i : i + INSERT_BATCH]})
        kb.db.run(
            "UPSERT $doc MERGE $data RETURN NONE;",
            {
                "doc": doc,
                "data": without_none(
                    {
                        "origin": src,
                        "content_type": fetched.content_type,
                        "raw_key": raw,
                        "text_key": text_key(digest),
                        "title": extracted.title,
                        "pages": sum(1 for p in extracted.pages if p.number is not None) or None,
                        "chunk_count": len(rows),
                    }
                ),
            },
        )
        chunk_count = len(rows)

    kb.db.run(
        """
        INSERT RELATION INTO fetched {in: $src, out: $doc, http_status: $status, via: $via}
            ON DUPLICATE KEY UPDATE last_seen_at = time::now(), http_status = $input.http_status RETURN NONE;
        LET $prev = (SELECT VALUE current FROM ONLY $src);
        IF $prev != NONE AND $prev != $doc { UPDATE $prev SET superseded_at = time::now() RETURN NONE; };
        UPDATE $doc SET superseded_at = NONE RETURN NONE;
        UPDATE $src MERGE $meta RETURN NONE;
        UPDATE $src SET last_fetched_at = time::now(), last_error = NONE RETURN NONE;
        """,
        {
            "src": src,
            "doc": doc,
            "status": fetched.status,
            "via": fetched.via,
            "meta": without_none({"current": doc, "title": extracted.title}),
        },
    )

    links = _matching_links(extracted.links, spec.follow)
    _record_links(kb, src, spec, links)
    return IngestResult(url, "new" if is_new else "unchanged", chunk_count, links)


def crawl(
    kb: KB,
    seed: SourceSpec,
    refresh: bool = False,
    max_pages: int = 200,
    delay: float = 0.5,
    on_result=None,
) -> list[IngestResult]:
    """Breadth-first crawl from a seed, following links that match seed.follow up to seed.depth."""
    robots: dict[str, RobotFileParser | None] = {}
    queue: deque[tuple[SourceSpec, int]] = deque([(seed, 0)])
    seen: set[str] = set()
    results: list[IngestResult] = []

    while queue and len(results) < max_pages:
        spec, level = queue.popleft()
        url = normalize_url(spec.url)
        if url in seen:
            continue
        seen.add(url)

        if not _allowed(robots, url):
            result = IngestResult(url, "skipped", error="disallowed by robots.txt")
        elif level > 0 and not refresh and kb.is_fetched(url):
            # Still walk its known links, so an incremental crawl reaches new pages deeper down.
            known = kb.db.one("SELECT VALUE ->links_to->source.url FROM ONLY $src;", {"src": RecordID("source", url)})
            result = IngestResult(url, "skipped", links=[(u, "") for u in known or []], error="already fetched")
        else:
            result = ingest_url(kb, spec)
            time.sleep(delay)
        results.append(result)
        if on_result:
            on_result(result)

        if level < seed.depth:
            for link, _anchor in result.links:
                child = replace(spec, url=link, authority=classify_authority(link, spec.authority))
                queue.append((child, level + 1))
    return results


def ingest_pending(kb: KB, limit: int = 100, delay: float = 0.5, on_result=None) -> list[IngestResult]:
    """Fetch sources that were discovered through links but never fetched."""
    pending = kb.db.one(
        "SELECT url, authority, jurisdiction, agency, tags FROM source WHERE current = NONE AND last_error = NONE LIMIT $n;",
        {"n": limit},
    )
    results = []
    for row in pending:
        spec = SourceSpec(
            url=row["url"],
            authority=row["authority"],
            jurisdiction=row.get("jurisdiction"),
            agency=row.get("agency"),
            tags=row.get("tags") or [],
        )
        result = ingest_url(kb, spec)
        results.append(result)
        if on_result:
            on_result(result)
        time.sleep(delay)
    return results


def _upsert_source(kb: KB, src: RecordID, url: str, spec: SourceSpec) -> None:
    data = without_none(
        {
            "url": url,
            "domain": urlsplit(url).netloc,
            "authority": spec.authority if spec.authority != "unknown" else None,
            "jurisdiction": spec.jurisdiction,
            "agency": spec.agency,
        }
    )
    kb.db.run(
        "UPSERT $src MERGE $data RETURN NONE; UPDATE $src SET tags = array::union(tags, $tags) RETURN NONE;",
        {"src": src, "data": data, "tags": spec.tags},
    )


def _matching_links(links: list[tuple[str, str]], patterns: list[str]) -> list[tuple[str, str]]:
    if not patterns:
        return []
    compiled = [re.compile(p) for p in patterns]
    found: dict[str, str] = {}
    for href, anchor in links:
        href = normalize_url(href)
        if href.startswith("http") and any(p.search(href) for p in compiled):
            found.setdefault(href, anchor)
    return list(found.items())


def _record_links(kb: KB, src: RecordID, spec: SourceSpec, links: list[tuple[str, str]]) -> None:
    """Create stub sources for discovered links (so they can be fetched later) and link edges."""
    if not links:
        return
    stubs, edges = [], []
    for href, anchor in links:
        target = RecordID("source", href)
        stubs.append(
            without_none(
                {
                    "id": target,
                    "url": href,
                    "domain": urlsplit(href).netloc,
                    "authority": classify_authority(href, "unknown"),
                    "jurisdiction": spec.jurisdiction,
                    "agency": spec.agency,
                    "tags": spec.tags,
                }
            )
        )
        edges.append(without_none({"in": src, "out": target, "anchor": anchor or None}))
    kb.db.run(
        """
        INSERT IGNORE INTO source $stubs RETURN NONE;
        INSERT RELATION INTO links_to $edges ON DUPLICATE KEY UPDATE anchor = $input.anchor RETURN NONE;
        """,
        {"stubs": stubs, "edges": edges},
    )


def _allowed(cache: dict[str, RobotFileParser | None], url: str) -> bool:
    parts = urlsplit(url)
    origin = f"{parts.scheme}://{parts.netloc}"
    if origin not in cache:
        # Fetched with our own client: RobotFileParser.read() uses urllib's default user agent,
        # which some sites block, and it treats a 403 as "disallow everything".
        parser: RobotFileParser | None = None
        try:
            resp = httpx.get(f"{origin}/robots.txt", headers={"User-Agent": USER_AGENT}, timeout=15)
            if resp.status_code == 200:
                parser = RobotFileParser()
                parser.parse(resp.text.splitlines())
        except httpx.HTTPError:
            pass  # unreachable robots.txt: allow
        cache[origin] = parser
    parser = cache[origin]
    return parser is None or parser.can_fetch(USER_AGENT, url)
