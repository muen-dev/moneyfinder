"""The company's own website via Firecrawl: map the site, then scrape the pages that matter."""

import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit

from .. import config
from ..enrich import year
from ..profile import CollectorResult, clean_text
from ..providers import ProviderError, now
from . import Context, fact, same_site, strip_url

NAME = "website"
VIA = "firecrawl"

# Page kinds worth scraping besides the homepage, matched on the URL path.
PAGE_KINDS = {
    "about": r"/(about|about-us|our-story|story|history|company|who-we-are|mission|our-team|impact)(/|\.html?$|$)",
    "contact": r"/(contact|contact-us|visit|find-us|get-in-touch)(/|\.html?$|$)",
    "careers": r"/(careers?|jobs|join-us|join-our-team|work-with-us|hiring|employment)(/|\.html?$|$)",
    "locations": r"/(locations?|stores?|store-locator|retail|restaurants|offices?|find-a-location|our-locations)(/|\.html?$|$)",
}

SOCIAL = {
    "linkedin": r"^https://([a-z]{2,3}\.)?(www\.)?linkedin\.com/company/[A-Za-z0-9_%.-]+",
    "x": r"^https://(www\.)?(twitter|x)\.com/[A-Za-z0-9_]{1,30}/?$",
    "facebook": r"^https://(www\.)?facebook\.com/[A-Za-z0-9_.-]+/?$",
    "instagram": r"^https://(www\.)?instagram\.com/[A-Za-z0-9_.]+/?$",
    "youtube": r"^https://(www\.)?youtube\.com/(@|c/|channel/|user/)[A-Za-z0-9_.-]+/?$",
    "tiktok": r"^https://(www\.)?tiktok\.com/@[A-Za-z0-9_.]+/?$",
}

# Hosted job boards: a link to one from the site is a hiring signal on its own.
JOB_BOARDS = r"^https://(boards\.greenhouse\.io|job-boards\.greenhouse\.io|jobs\.lever\.co|jobs\.ashbyhq\.com|[a-z0-9-]+\.workable\.com|apply\.workable\.com|[a-z0-9-]+\.bamboohr\.com|jobs\.smartrecruiters\.com|[a-z0-9-]+\.myworkdayjobs\.com|[a-z0-9-]+\.applytojob\.com|[a-z0-9-]+\.recruitee\.com|wellfound\.com/company)/"

EXTRACT_PROMPT = (
    "Extract facts about the company that owns this website, as stated on this page. "
    "Leave a field empty when the page does not state it. Do not guess."
)
EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "company_name": {"type": "string", "description": "Brand name the company uses"},
        "legal_name": {"type": "string", "description": "Legal entity name, e.g. from the footer copyright (Acme LLC)"},
        "description": {"type": "string", "description": "One or two sentences on what the company does"},
        "products_services": {"type": "array", "items": {"type": "string"}},
        "industry": {"type": "string"},
        "headquarters_address": {"type": "string", "description": "Street address of the main office"},
        "other_locations": {"type": "array", "items": {"type": "string"}, "description": "Addresses of other stores or offices"},
        "phone": {"type": "string"},
        "founded_year": {"type": "string"},
        "employee_count": {"type": "string", "description": "Number of employees or team size, if stated"},
        "open_roles": {
            "type": "array",
            "items": {"type": "object", "properties": {"title": {"type": "string"}, "location": {"type": "string"}}},
        },
        "ownership_certifications": {
            "type": "array",
            "items": {"type": "string"},
            "description": "e.g. women-owned, minority-owned, veteran-owned, MWBE, B Corp, union shop",
        },
        "rd_or_technology": {"type": "array", "items": {"type": "string"}, "description": "Research, patents, proprietary technology"},
        "expansion_or_investment": {"type": "array", "items": {"type": "string"}, "description": "New locations, facilities, equipment, funding"},
        "awards": {"type": "array", "items": {"type": "string"}},
    },
}


def collect(ctx: Context) -> CollectorResult:
    result = CollectorResult(NAME)
    providers = ctx.providers
    home = f"https://{ctx.domain}/"
    try:
        links = providers.firecrawl_map(home)
    except ProviderError as e:
        if "no API key" in str(e):
            raise
        links = []
        result.context["map_error"] = str(e)
    pages = {"home": home} | pick_pages([link.get("url", "") for link in links], ctx.domain)
    with ThreadPoolExecutor(max_workers=3) as pool:
        scraped = list(pool.map(lambda item: _scrape(providers, *item), pages.items()))
    if not any(data for _, _, data, _ in scraped):
        errors = "; ".join(err for *_, err in scraped if err)
        raise ProviderError(f"no page could be scraped ({errors})")
    texts = []
    for kind, url, data, err in scraped:
        if data:
            texts.append(f"[{kind}] {clean_text(data.get('markdown') or '', config.MAX_PAGE_CHARS // 4)}")
            _facts_from_page(ctx, result, kind, url, data)
        elif err:
            result.context.setdefault("page_errors", []).append(f"{kind}: {err}")
    result.context["text"] = "\n\n".join(texts)
    return result


def pick_pages(urls: list[str], domain: str) -> dict[str, str]:
    """For each page kind, the shortest same-site URL whose path matches it."""
    chosen: dict[str, str] = {}
    for url in sorted({strip_url(u) for u in urls if same_site(u, domain)}, key=len):
        path = urlsplit(url).path.lower()
        for kind, pattern in PAGE_KINDS.items():
            if kind not in chosen and re.search(pattern, path):
                chosen[kind] = url
    return chosen


def _scrape(providers, kind: str, url: str):
    formats = ["markdown", "links", {"type": "json", "prompt": EXTRACT_PROMPT, "schema": EXTRACT_SCHEMA}]
    try:
        # The homepage footer carries social links, the copyright legal name and often the address.
        return kind, url, providers.firecrawl_scrape(url, formats, only_main_content=kind != "home"), None
    except ProviderError as e:
        return kind, url, None, str(e)


def _facts_from_page(ctx: Context, result: CollectorResult, kind: str, url: str, data: dict) -> None:
    meta = data.get("metadata") or {}
    page_url = strip_url(meta.get("sourceURL") or meta.get("url") or url)
    if not same_site(page_url, ctx.domain):
        page_url = url  # a redirect off-site: cite what we asked for
    at = now()
    info = data.get("json") or {}
    if not isinstance(info, dict):
        info = {}

    def add(field_name, value, confidence, note=""):
        if value not in (None, "", [], {}):
            result.facts.append(fact(field_name, value, page_url, VIA, at, confidence, NAME, note))

    if kind == "home":
        site_name = meta.get("ogSiteName") or info.get("company_name")
        ctx.add_name(_text(site_name))
        add("description", _text(meta.get("description") or meta.get("ogDescription")), 0.5, "page meta description")
    ctx.add_name(_text(info.get("company_name")))
    ctx.add_name(_text(info.get("legal_name")))
    add("legal_name", _text(info.get("legal_name")), 0.55)
    if info.get("company_name") and info.get("legal_name") and _text(info["company_name"]).lower() != _text(info["legal_name"]).lower():
        add("dba", _text(info.get("company_name")), 0.5)
    add("description", _text(info.get("description")), 0.65)
    add("industry", _text(info.get("industry")), 0.55)
    for item in _list(info.get("products_services"))[:12]:
        add("products_services", item, 0.6)
    address = _text(info.get("headquarters_address"))
    if address:
        add("hq_address", address, 0.65 if kind in ("contact", "about", "locations") else 0.55)
        city = re.search(r",\s*([A-Za-z .]+),?\s+(NY|New York)\b", address)
        if city and not ctx.city:
            ctx.city = city.group(1).strip()
    for loc in _list(info.get("other_locations"))[:20]:
        add("other_locations", loc, 0.6)
    add("phone", _text(info.get("phone")), 0.6)
    add("founded_year", year(info.get("founded_year")), 0.6)
    add("employee_count", _text(info.get("employee_count")), 0.45, "self-reported on website")
    for role in (info.get("open_roles") or [])[:25]:
        if isinstance(role, dict) and role.get("title"):
            add("hiring_signals", {"title": f"Open role: {_text(role['title'])}", "detail": _text(role.get("location"))}, 0.7)
    for item in _list(info.get("ownership_certifications")):
        add("ownership_certifications", item, 0.55, "self-reported on website")
    for item in _list(info.get("rd_or_technology")):
        add("rd_tech_signals", {"title": item}, 0.5)
    for item in _list(info.get("expansion_or_investment")):
        add("expansion_signals", {"title": item}, 0.5)
    for item in _list(info.get("awards")):
        add("awards", {"title": item}, 0.5)

    for link in data.get("links") or []:
        if not isinstance(link, str):
            continue
        link = strip_url(link)
        for network, pattern in SOCIAL.items():
            if re.match(pattern, link):
                add("social_links", link, 0.8, f"{network} link on the company site")
                if network == "linkedin":
                    add("linkedin_url", link.rstrip("/"), 0.85, "linked from the company site")
                    ctx.linkedin_url = ctx.linkedin_url or link.rstrip("/")
        if re.match(JOB_BOARDS, link):
            add("hiring_signals", {"title": "Hosted job board linked from the site", "url": link}, 0.6)


def _text(value) -> str:
    return clean_text(value, 400) if isinstance(value, (str, int, float)) else ""


def _list(value) -> list[str]:
    if isinstance(value, str):
        value = [value]
    return [t for t in (_text(v) for v in (value or []) if isinstance(v, (str, int, float))) if t]
