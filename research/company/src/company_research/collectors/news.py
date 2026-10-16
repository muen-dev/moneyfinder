"""Web and news search (Tavily, Nimble fallback) for hiring, expansion, R&D, awards and certifications.

Results only count if they mention the company; each is filed under the signals its text matches.
"""

import re

from ..profile import CollectorResult, clean_text
from ..providers import MissingKey, ProviderError, now
from . import Context, fact, mentions, strip_url

NAME = "news"

SIGNALS = {
    "hiring_signals": r"\b(hiring|hires|job openings?|new jobs|jobs? fair|workforce|headcount|recruit\w*|apprentice\w*|internships?)\b",
    "expansion_signals": r"\b(expan\w+|new (store|location|office|headquarters|facility|plant|warehouse)|opens?|opening|relocat\w+|lease[sd]?|invest\w*|raises?|raised|funding|series [a-e]|acquir\w+|capital|square feet|sq\.? ?ft)\b",
    "rd_tech_signals": r"\b(r&d|research and development|patents?|patented|engineers?|engineering|proprietary|artificial intelligence|machine learning|ai-powered)\b",
    "awards": r"\b(awards?|awarded|winner|honou?red|recogni[sz]ed|named (to|one of)|best of|top \d+)\b",
}
CERTIFICATIONS = {
    "women-owned (mentioned in press)": r"\b(women[- ]owned|woman[- ]owned|wbe)\b",
    "minority-owned (mentioned in press)": r"\b(minority[- ]owned|mbe|black[- ]owned|latino[- ]owned|hispanic[- ]owned|asian[- ]owned)\b",
    "M/WBE certified (mentioned in press)": r"\b(m/?wbe)\b",
    "veteran-owned (mentioned in press)": r"\b(veteran[- ]owned|sdvob|sdvosb)\b",
    "B Corp (mentioned in press)": r"\b(b corp|certified b corporation)\b",
    "disadvantaged business (mentioned in press)": r"\b(dbe|disadvantaged business)\b",
}

# Sites whose pages are about many companies or are the company's own pages (covered elsewhere).
SKIP_HOSTS = ("linkedin.com", "bbb.org", "facebook.com", "instagram.com", "x.com", "twitter.com", "youtube.com", "tiktok.com")

# Without the domain, a result also has to place the company in New York: names are often shared
# (a "Main Capital" private equity firm in Amsterdam is a different company).
NY_PLACES = r"New York|NYC|NY|Brooklyn|Queens|Bronx|Manhattan|Staten Island|Long Island|Westchester"


def collect(ctx: Context) -> CollectorResult:
    result = CollectorResult(NAME)
    name = ctx.name
    queries = [
        (f'"{name}" New York hiring OR expansion OR "new location" OR opening OR investment', {"topic": "news", "time_range": "year"}),
        (f'"{name}" certified OR "women-owned" OR "minority-owned" OR "veteran-owned" OR award OR patent OR "research and development"', {}),
    ]
    seen, errors = set(), []
    for query, options in queries:
        try:
            hits, via = ctx.providers.search(query, max_results=8, **options)
        except MissingKey:
            raise
        except ProviderError as e:
            errors.append(str(e))
            continue
        for hit in hits:
            url = strip_url(hit.get("url", ""))
            host = re.sub(r"^https?://(www\.)?", "", url).split("/")[0]
            if not url.startswith("https://") or url in seen or host.endswith(ctx.domain) or host.endswith(SKIP_HOSTS):
                continue
            text = f"{hit.get('title', '')} {hit.get('content', '')}"
            if not mentions(text, ctx.names or [name], ctx.domain) or not _placed(text, ctx):
                continue
            seen.add(url)
            _classify(result, hit, url, via, text)
    if errors and not seen:
        raise ProviderError("; ".join(errors))
    return result


def _placed(text: str, ctx: Context) -> bool:
    if ctx.domain in text.lower():
        return True
    places = NY_PLACES + (f"|{re.escape(ctx.city)}" if ctx.city else "")
    return re.search(rf"\b({places})\b", text) is not None


def _classify(result: CollectorResult, hit: dict, url: str, via: str, text: str) -> None:
    at = now()
    item = {
        "title": clean_text(hit.get("title") or url, 200),
        "url": url,
        "date": (hit.get("published_date") or "")[:10] or None,
        "snippet": clean_text(hit.get("content") or "", 300),
    }
    matched = False
    for field_name, pattern in SIGNALS.items():
        if re.search(pattern, text, re.I):
            result.facts.append(fact(field_name, item, url, via, at, 0.45, NAME, "keyword match in search result"))
            matched = True
    for label, pattern in CERTIFICATIONS.items():
        if re.search(pattern, text, re.I):
            result.facts.append(fact("ownership_certifications", label, url, via, at, 0.35, NAME, "keyword in search result; verify"))
    if not matched:
        result.facts.append(fact("news", item, url, via, at, 0.4, NAME))
