"""LinkedIn company page, public data only: found by search, read from the search snippet.

We never request linkedin.com ourselves or through a scraper: no login, cookies or auth walls.
"""

import re

from ..enrich import name_similarity
from ..profile import CollectorResult, clean_text
from ..providers import now
from . import Context, fact

NAME = "linkedin"
COMPANY_URL = re.compile(r"^https://(?:[a-z]{2,3}\.)?(?:www\.)?linkedin\.com/company/([a-z0-9_%.-]+)", re.I)

SNIPPET_FIELDS = {
    "linkedin_followers": r"([\d][\d,.]*\s?[KkMm]?)\s+followers",
    "employee_count": r"(?:company size|size)[:\s]+([\d,]+\s?(?:-|–|to)\s?[\d,]+|[\d,]+\+)\s*employees",
    "employee_count_alt": r"\b([\d,]+\s?(?:-|–)\s?[\d,]+|[\d,]+\+)\s+employees\b",
    "industry": r"industry[:\s]+([A-Z][A-Za-z,&/ -]{2,60}?)(?=\s*(?:[|·•\n]|company size|headquarters|type|founded|$))",
    "hq_address": r"headquarters[:\s]+([A-Z][A-Za-z .,'-]{2,60}?)(?=\s*(?:[|·•\n#\[]|type|founded|specialties|social|$))",
    "employee_count_now": r"employees\s*-\s*now:\s*([\d,]+)",
    "founded_year": r"founded[:\s]+(1[89]\d{2}|20\d{2})",
}


def collect(ctx: Context) -> CollectorResult:
    result = CollectorResult(NAME)
    query = f"{ctx.name} company LinkedIn"
    hits, via = ctx.providers.search(query, include_domains=["linkedin.com"], max_results=8)
    url, hit = best_page(hits, ctx)
    if not url:
        result.error = "no LinkedIn company page found"
        return result
    at = now()
    from_site = bool(ctx.linkedin_url and _slug(ctx.linkedin_url) == _slug(url))
    confidence = 0.75 if from_site else 0.5
    note = "from search snippet" + ("" if from_site else "; matched by name")
    result.facts.append(fact("linkedin_url", url, url, via, at, confidence, NAME, note))
    snippet = f"{hit.get('title', '')} | {hit.get('content', '')}"
    for key, value in parse_snippet(snippet).items():
        result.facts.append(fact(key, value, url, via, at, confidence * 0.85, NAME, note))
    return result


def best_page(hits: list[dict], ctx: Context) -> tuple[str | None, dict]:
    wanted = _slug(ctx.linkedin_url) if ctx.linkedin_url else None
    best, best_score, best_hit = None, 0.0, {}
    for hit in hits:
        match = COMPANY_URL.match(hit.get("url", ""))
        if not match:
            continue
        url = f"https://www.linkedin.com/company/{match.group(1).lower()}"
        title = re.split(r"\s[|-]\s", hit.get("title", ""))[0]
        score = max(name_similarity(title, n) for n in (ctx.names or [ctx.name]))
        if wanted and match.group(1).lower() == wanted:
            score += 2.0
        if score > best_score:
            best, best_score, best_hit = url, score, hit
    return (best, best_hit) if best_score >= 0.5 else (None, {})


def parse_snippet(text: str) -> dict:
    text = clean_text(text, 2000)
    found = {}
    for key, pattern in SNIPPET_FIELDS.items():
        match = re.search(pattern, text, re.I)
        if not match:
            continue
        field_name = key.removesuffix("_alt").removesuffix("_now")
        if field_name in found:
            continue
        value = match.group(1).strip(" .,")
        if key == "employee_count_now":
            value = f"{value} employees on LinkedIn"
        elif field_name == "employee_count":
            value = f"{value} employees (LinkedIn range)"
        if field_name == "founded_year":
            value = int(value)
        found[field_name] = value
    return found


def _slug(url: str | None) -> str | None:
    match = COMPANY_URL.match(url or "")
    return match.group(1).lower() if match else None
