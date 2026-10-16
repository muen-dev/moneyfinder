"""Firmographics (employees, HQ, founded year, industry) from Firecrawl Alexandria data providers.

fullenrich `companies/lookup` first (5 credits); Apollo `companies/enrich` (30 credits) only when
fullenrich has no record for the domain. Uses the Firecrawl key; the raw response is recorded like
every other call.
"""

from ..profile import CollectorResult
from ..providers import MissingKey, now
from . import Context, fact

NAME = "firmographics"
FULLENRICH = ("fullenrich", "companies/lookup")
APOLLO = ("apollo", "companies/enrich")


def collect(ctx: Context) -> CollectorResult:
    if not ctx.providers.available("firecrawl"):
        raise MissingKey("firecrawl: no API key (set FIRECRAWL_API_KEY)")
    result = CollectorResult(NAME)
    data = ctx.providers.alexandria(*FULLENRICH, {"domain": ctx.domain})
    company = _match((data.get("companies") or []), ctx.domain)
    if company:
        result.facts = fullenrich_facts(company, ctx.domain, now())
        result.context["provider"] = "fullenrich"
        return result
    data = ctx.providers.alexandria(*APOLLO, {"domain": ctx.domain})
    org = data.get("organization") or {}
    if org:
        result.facts = apollo_facts(org, ctx.domain, now())
        result.context["provider"] = "apollo"
        return result
    result.error = "no firmographics record for this domain (fullenrich, apollo)"
    return result


def _match(companies: list, domain: str) -> dict | None:
    for company in companies:
        if not isinstance(company, dict):
            continue
        found = (company.get("domain") or "").lower().removeprefix("www.")
        if not found or found == domain or found.endswith(f".{domain}"):
            return company
    return None


def _source(provider: str, capability: str, domain: str) -> str:
    return f"alexandria:{provider}/{capability}?domain={domain}"


def fullenrich_facts(c: dict, domain: str, at: str) -> list:
    url, via = _source(*FULLENRICH, domain), "fullenrich via Firecrawl Alexandria"
    facts = []

    def add(field_name, value, confidence, note=""):
        if value not in (None, "", [], {}):
            facts.append(fact(field_name, value, url, via, at, confidence, NAME, note))

    add("employee_count", c.get("headcount"), 0.8, f"headcount; range {c.get('headcount_range')}" if c.get("headcount_range") else "headcount")
    if c.get("headcount") in (None, "") and c.get("headcount_range"):
        add("employee_count", f"{c['headcount_range']} employees (range)", 0.6)
    add("founded_year", _year(c.get("year_founded")), 0.8)
    add("hq_address", _hq(((c.get("locations") or {}).get("headquarters")) or {}), 0.75)
    add("industry", ((c.get("industry") or {}).get("main_industry")), 0.7)
    add("description", c.get("description"), 0.6)
    profile = ((c.get("social_profiles") or {}).get("professional_network")) or {}
    add("linkedin_url", profile.get("url"), 0.8)
    for specialty in (c.get("specialties") or [])[:8]:
        add("products_services", specialty, 0.5)
    return facts


def apollo_facts(o: dict, domain: str, at: str) -> list:
    url, via = _source(*APOLLO, domain), "apollo via Firecrawl Alexandria"
    facts = []

    def add(field_name, value, confidence, note=""):
        if value not in (None, "", [], {}):
            facts.append(fact(field_name, value, url, via, at, confidence, NAME, note))

    add("employee_count", o.get("estimated_num_employees"), 0.75, "estimated")
    add("founded_year", _year(o.get("founded_year")), 0.75)
    address = o.get("raw_address") or ", ".join(
        str(p) for p in (o.get("street_address"), o.get("city"), o.get("state"), o.get("postal_code"), o.get("country")) if p
    )
    add("hq_address", address, 0.7)
    add("industry", o.get("industry"), 0.65)
    add("description", o.get("short_description"), 0.55)
    add("linkedin_url", o.get("linkedin_url"), 0.75)
    phone = (o.get("primary_phone") or {}).get("number") if isinstance(o.get("primary_phone"), dict) else o.get("phone")
    add("phone", phone, 0.6)
    for code in (o.get("naics_codes") or [])[:2]:
        add("naics", {"code": str(code), "title": ""}, 0.6, "Apollo NAICS code")
    return facts


def _hq(hq: dict) -> str | None:
    if not hq:
        return None
    if hq.get("line1") and hq.get("line2"):
        return f"{hq['line1']}, {hq['line2']}"
    parts = [hq.get("line1"), hq.get("city"), hq.get("region"), hq.get("country_code")]
    return ", ".join(p for p in parts if p) or None


def _year(value) -> int | None:
    try:
        year = int(value)
    except (TypeError, ValueError):
        return None
    return year if 1700 <= year <= 2100 else None
