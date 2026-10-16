"""Better Business Bureau profile: found through search, read through Firecrawl (Nimble as fallback).

bbb.org's robots.txt allows /us/*/*/profile/* pages (without query strings), which is all we read.
"""

import re

from ..domain import InvalidDomain, normalize
from ..enrich import name_key, name_similarity, year
from ..profile import CollectorResult, clean_text
from ..providers import MissingKey, ProviderError, now
from . import Context, fact, mentions

NAME = "bbb"
PROFILE_URL = re.compile(r"^https://(?:www\.)?bbb\.org/(us|ca)/[a-z]{2}/[a-z0-9-]+/profile/[a-z0-9-]+/[a-z0-9-]+-\d+-\d+")

EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "business_name": {"type": "string"},
        "bbb_rating": {"type": "string", "description": "Letter grade such as A+, A, B, or NR"},
        "accredited": {"type": "boolean", "description": "Whether the business is BBB Accredited"},
        "accredited_since": {"type": "string"},
        "years_in_business": {"type": "string"},
        "business_started": {"type": "string"},
        "business_incorporated": {"type": "string"},
        "entity_type": {"type": "string", "description": "Type of Entity, e.g. Corporation, LLC"},
        "number_of_employees": {"type": "string"},
        "address": {"type": "string"},
        "phone": {"type": "string"},
        "website": {"type": "string"},
        "business_categories": {"type": "array", "items": {"type": "string"}},
    },
}

# Plain-text fallbacks for the same fields, applied to the page markdown.
PATTERNS = {
    "bbb_rating": r"BBB Rating:?\s*\**\s*([A-F][+-]?|NR)\b",
    "accredited_since": r"Accredited Since:?\s*\**\s*([0-9/]{6,10})",
    "years_in_business": r"Years in Business:?\s*\**\s*(\d{1,3})",
    "business_started": r"Business Started:?\s*\**\s*([0-9/]{4,10})",
    "business_incorporated": r"Business Incorporated:?\s*\**\s*([0-9/]{4,10})",
    "entity_type": r"Type of Entity:?\s*\**\s*([A-Za-z ()-]{3,40})",
    "number_of_employees": r"Number of Employees:?\s*\**\s*([\d,]+)",
}


def collect(ctx: Context) -> CollectorResult:
    result = CollectorResult(NAME)
    query = f"{ctx.name} {ctx.city or 'New York'} BBB business profile"
    hits, via_search = ctx.providers.search(query, include_domains=["bbb.org"], max_results=8)
    url, hit = best_profile(hits, ctx)
    if not url:
        result.status = "ok"
        result.error = "no BBB profile found"
        return result

    info, via = _read_profile(ctx, url)
    at = now()
    name = clean_text(info.get("business_name") or hit.get("title", "").split(" | ")[0], 120)
    site = info.get("website") or ""
    confidence, note = _match(ctx, name, site)

    def add(field_name, value, conf=confidence, extra=""):
        if value not in (None, "", []):
            result.facts.append(fact(field_name, value, url, via, at, conf, NAME, " ".join(filter(None, [note, extra]))))

    add("bbb_profile_url", url)
    add("bbb_rating", clean_text(info.get("bbb_rating") or "", 4).upper() or None)
    accredited = info.get("accredited")
    if accredited is None and info.get("accredited_since"):
        accredited = True
    if isinstance(accredited, bool):
        add("bbb_accredited", accredited, extra=f"since {info['accredited_since']}" if info.get("accredited_since") else "")
    add("years_in_business", _int(info.get("years_in_business")))
    add("founded_year", year(info.get("business_started")), confidence * 0.9, "BBB 'Business Started'")
    add("entity_type", clean_text(info.get("entity_type") or "", 60) or None, confidence * 0.8, "BBB 'Type of Entity'")
    add("employee_count", clean_text(info.get("number_of_employees") or "", 40) or None, confidence * 0.8, "BBB")
    add("hq_address", clean_text(info.get("address") or "", 200) or None, confidence * 0.9)
    add("phone", clean_text(info.get("phone") or "", 40) or None, confidence * 0.8)
    add("legal_name", name or None, confidence * 0.6, "BBB business name")
    for category in (info.get("business_categories") or [])[:5]:
        if isinstance(category, str):
            add("industry", clean_text(category, 80), confidence * 0.6, "BBB category")
    result.context["search_via"] = via_search
    return result


def best_profile(hits: list[dict], ctx: Context) -> tuple[str | None, dict]:
    """Highest-scoring bbb.org profile URL among search hits, trimmed to the profile root."""
    best, best_score, best_hit = None, 0.0, {}
    for hit in hits:
        match = PROFILE_URL.match(hit.get("url", "").lower())
        if not match:
            continue
        title = hit.get("title", "").split("|")[0]
        # The listing must carry every word of the name: "Capital Group" is not "Main Capital".
        score = max((name_similarity(title, n) for n in (ctx.names or [ctx.name]) if _covers(title, n)), default=0.0)
        if mentions(hit.get("content", ""), [], ctx.domain):
            score += 1.0
        if score > best_score:
            best, best_score, best_hit = match.group(0), score, hit
    return (best, best_hit) if best_score > 0 else (None, {})


def _covers(title: str, name: str) -> bool:
    words = set(name_key(name).split())
    return bool(words) and words <= set(name_key(title).split())


def _read_profile(ctx: Context, url: str) -> tuple[dict, str]:
    """Structured fields from the profile page: Firecrawl JSON first, Nimble markdown if that fails."""
    errors = []
    try:
        data = ctx.providers.firecrawl_scrape(url, ["markdown", {"type": "json", "schema": EXTRACT_SCHEMA}], only_main_content=False)
        info = data.get("json") if isinstance(data.get("json"), dict) else {}
        return _fill_from_text(dict(info), data.get("markdown") or ""), "firecrawl"
    except ProviderError as e:
        errors.append(str(e))
    try:
        markdown = ctx.providers.nimble_extract(url)
        return _fill_from_text({}, markdown), "nimble"
    except (MissingKey, ProviderError) as e:
        errors.append(str(e))
    raise ProviderError("could not read BBB profile: " + "; ".join(errors))


def _fill_from_text(info: dict, markdown: str) -> dict:
    for key, pattern in PATTERNS.items():
        if not info.get(key) and (m := re.search(pattern, markdown, re.I)):
            info[key] = m.group(1).strip()
    if "accredited" not in info and markdown:
        if re.search(r"\bnot BBB Accredited\b", markdown, re.I):
            info["accredited"] = False
        elif re.search(r"\bBBB Accredited Business\b", markdown, re.I):
            info["accredited"] = True
    return info


def _match(ctx: Context, name: str, site: str) -> tuple[float, str]:
    """How sure we are that the profile is this company: its website beats a name match."""
    try:
        if site and normalize(site) == ctx.domain:
            return 0.85, ""
    except InvalidDomain:
        pass
    similarity = max((name_similarity(name, n) for n in ctx.names or [ctx.name]), default=0)
    if similarity >= 0.99:
        return 0.65, "matched by name only"
    return 0.35, "BBB profile may be a different business (weak name match)"


def _int(value):
    match = re.search(r"\d{1,3}", str(value or ""))
    return int(match.group(0)) if match else None
