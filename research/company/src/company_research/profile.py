"""CompanyProfile: facts from many sources, merged deterministically, each with provenance.

A field holds a list of claims sorted by confidence. For single-valued fields the first claim is
the best guess and the rest are conflicting values, kept side by side with their own sources.
"""

import re
from dataclasses import dataclass, field
from typing import Any

SCHEMA_VERSION = 1

# name -> (label, multi-valued?)
FIELDS: dict[str, tuple[str, bool]] = {
    "legal_name": ("Legal name", False),
    "dba": ("Doing business as", False),
    "description": ("Description", False),
    "products_services": ("Products and services", True),
    "industry": ("Industry", False),
    "naics": ("NAICS (guess)", False),
    "hq_address": ("Headquarters address", False),
    "nyc_borough": ("NYC borough", False),
    "county": ("NY county", False),
    "other_locations": ("Other locations", True),
    "employee_count": ("Employees", False),
    "founded_year": ("Founded", False),
    "entity_type": ("Entity type", False),
    "state_of_formation": ("State of formation", False),
    "ny_dos_id": ("NY DOS id", False),
    "ny_dos_filing_date": ("NY DOS filing date", False),
    "ownership_certifications": ("Ownership and certifications", True),
    "nyc_licenses": ("NYC DCWP licenses", True),
    "hiring_signals": ("Hiring", True),
    "rd_tech_signals": ("R&D and technology", True),
    "expansion_signals": ("Expansion and capital investment", True),
    "awards": ("Awards and recognition", True),
    "news": ("Other news", True),
    "bbb_rating": ("BBB rating", False),
    "bbb_accredited": ("BBB accredited", False),
    "bbb_profile_url": ("BBB profile", False),
    "years_in_business": ("Years in business (BBB)", False),
    "linkedin_url": ("LinkedIn", False),
    "linkedin_followers": ("LinkedIn followers", False),
    "phone": ("Phone", False),
    "social_links": ("Social links", True),
    "summary": ("Summary (LLM)", False),
    "incentive_signals": ("Incentive-relevant signals (LLM)", True),
}

MAX_VALUE_CHARS = 600
MAX_CLAIMS_PER_FIELD = 25


@dataclass
class Source:
    url: str
    via: str
    fetched_at: str

    def to_dict(self) -> dict:
        return {"url": self.url, "via": self.via, "fetched_at": self.fetched_at}


@dataclass
class Fact:
    """One collector's claim about one field."""

    field: str
    value: Any
    source: Source
    confidence: float
    collector: str
    note: str = ""


@dataclass
class CollectorResult:
    name: str
    status: str = "ok"  # ok | skipped | failed
    error: str | None = None
    duration_s: float = 0.0
    facts: list[Fact] = field(default_factory=list)
    context: dict = field(default_factory=dict)  # hand-offs to later collectors (e.g. company name)

    def summary(self) -> dict:
        return {
            "status": self.status,
            "error": self.error,
            "duration_s": round(self.duration_s, 1),
            "facts": len(self.facts),
        }


def clean_text(value: Any, limit: int = MAX_VALUE_CHARS) -> str:
    """Scraped text as a short single-line string: no control characters, bounded length."""
    text = re.sub(r"[\x00-\x1f\x7f​-‏ -‮⁦-⁩]+", " ", str(value))
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def clean_value(value: Any) -> Any:
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, dict):
        return {clean_text(k, 40): clean_value(v) for k, v in list(value.items())[:12] if v not in (None, "", [])}
    if isinstance(value, (list, tuple)):
        return [clean_value(v) for v in value[:12]]
    return clean_text(value)


def _key(value: Any) -> str:
    """Normalized form used to decide whether two claims say the same thing."""
    if isinstance(value, dict):
        value = value.get("url") or value.get("title") or value.get("name") or sorted(value.items())
    text = str(value).casefold()
    text = re.sub(r"https?://(www\.)?", "", text).rstrip("/")
    text = re.sub(r"[^\w]+", " ", text)
    text = re.sub(r"\b(the|inc|llc|l l c|corp|corporation|co|company|ltd|incorporated)\b", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def merge(facts: list[Fact]) -> dict[str, list[dict]]:
    """Group facts per field; identical values pool their sources, conflicting ones stay separate."""
    grouped: dict[str, dict[str, dict]] = {}
    for fact in facts:
        if fact.field not in FIELDS or fact.value in (None, "", [], {}):
            continue
        value = clean_value(fact.value)
        key = _key(value)
        if not key:
            continue
        claims = grouped.setdefault(fact.field, {})
        claim = claims.get(key)
        if claim is None:
            claim = claims[key] = {"value": value, "confidence": 0.0, "sources": [], "collectors": [], "_top": 0.0}
        if fact.confidence > claim["_top"]:  # show the spelling from the most confident source
            claim["value"], claim["_top"] = value, fact.confidence
        # Independent sources agreeing raise confidence (noisy-or), capped below certainty.
        claim["confidence"] = round(min(0.99, 1 - (1 - claim["confidence"]) * (1 - fact.confidence)), 2)
        if fact.collector not in claim["collectors"]:
            claim["collectors"].append(fact.collector)
        source = fact.source.to_dict()
        if fact.note:
            source["note"] = clean_text(fact.note, 200)
        if not any(s["url"] == source["url"] and s["via"] == source["via"] for s in claim["sources"]):
            claim["sources"].append(source)
    merged = {}
    for name in FIELDS:
        if name in grouped:
            for claim in grouped[name].values():
                claim.pop("_top", None)
            claims = sorted(grouped[name].values(), key=lambda c: (-c["confidence"], -len(c["sources"])))
            merged[name] = claims[:MAX_CLAIMS_PER_FIELD]
    return merged


def best_values(fields: dict[str, list[dict]]) -> dict[str, Any]:
    """Flat view for matching agents: top value of single fields, all values of multi fields."""
    best = {}
    for name, claims in fields.items():
        multi = FIELDS[name][1]
        best[name] = [c["value"] for c in claims] if multi else claims[0]["value"]
    return best


def build(
    domain: str,
    inputs: dict,
    results: list[CollectorResult],
    generated_at: str,
    extra_facts: list[Fact] | None = None,
) -> dict:
    facts = [f for r in results for f in r.facts] + list(extra_facts or [])
    fields = merge(facts)
    return {
        "schema_version": SCHEMA_VERSION,
        "domain": domain,
        "inputs": inputs,
        "generated_at": generated_at,
        "best": best_values(fields),
        "fields": fields,
        "collectors": {r.name: r.summary() for r in results},
    }
