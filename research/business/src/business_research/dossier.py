"""One form-ready dossier per business: public research, firmographics, email facts and matched credits.

Schema moneyfinder.dossier/v1 (the form filler and the SurrealDB loader code against it):
  business      best value per key (user > registry > enrichment > web > email > llm, then confidence)
  facts         every value with its source, source_kind, confidence and capture time
  email         what the fetched mail says (category counts, signals)
  credits       legal_research.match.match_programs output
  missing_info  fields tax-credit forms need that no source provided
Written to dossier.json next to the data it came from (git-ignored data dirs, owner-only).
"""

import json
import re
from datetime import UTC, datetime
from pathlib import Path

from company_research import store as company_store
from company_research.domain import normalize
from legal_research import store as legal_store
from legal_research.match import match_programs

from . import company, email_facts, inbox, store

SCHEMA = "moneyfinder.dossier/v1"
BUSINESS_KEYS = (
    "name", "legal_name", "dba", "website", "naics", "industry", "entity_type", "state_of_formation", "ny_dos_id",
    "hq_address", "county", "nyc_borough", "phone", "employees", "founded_year", "ein", "payroll_provider", "contact_email",
)
# Fact key -> business key, where they differ.
ALIASES = {"employee_count": "employees"}
KIND_RANK = {"user": 0, "registry": 1, "enrichment": 2, "web": 3, "email": 4, "llm": 5}
COLLECTOR_KIND = {
    "website": "web", "bbb": "web", "linkedin": "web", "news": "web",
    "nys_dos": "registry", "nyc_open_data": "registry", "firmographics": "enrichment", "llm": "llm",
}
# Fields common NY/federal credit applications ask for.
FORM_FIELDS = (
    "legal_name", "ein", "entity_type", "state_of_formation", "hq_address", "naics", "employees", "founded_year",
    "phone", "contact_email", "officer_name", "officer_title", "tax_year",
)
MULTI_LIMIT = 5


def build_for_domain(domain: str, business_id: str | None = None, *, use_llm: bool = True, write: bool = True) -> dict:
    """Dossier for a researched domain (research/company/data/<domain>), plus a business's mail if given."""
    domain = normalize(domain)
    profile = None
    if business_id:
        profile = company.profile(business_id)
    profile = profile or _read_profile(company_store.default_dir(domain))
    dossier = assemble(domain, profile, business_id, use_llm=use_llm)
    if write:
        out = company.business_dir(business_id) if business_id else company_store.default_dir(domain)
        write_dossier(out, dossier)
    return dossier


def build_for_business(business_id: str, *, use_llm: bool = True, write: bool = True) -> dict:
    """Dossier for a connected business: its company domain's research plus its fetched mail."""
    domain = company.get_domain(business_id)
    profile = company.profile(business_id)
    if domain and profile is None:
        profile = _read_profile(company_store.default_dir(domain))
    dossier = assemble(domain, profile, business_id, use_llm=use_llm)
    if write:
        write_dossier(company.business_dir(business_id), dossier)
    return dossier


def dossier_path(out_dir: Path) -> Path:
    return out_dir / "dossier.json"


def cached_for_domain(domain: str) -> dict | None:
    return _read_json(dossier_path(company_store.default_dir(normalize(domain))))


def cached_for_business(business_id: str) -> dict | None:
    return _read_json(dossier_path(company.business_dir(business_id)))


def write_dossier(out_dir: Path, dossier: dict) -> Path:
    path = dossier_path(out_dir)
    company._write(path, dossier)
    return path


def assemble(domain: str | None, profile: dict | None, business_id: str | None, *, use_llm: bool = True) -> dict:
    at = _now()
    facts = profile_facts(profile) if profile else []
    info = company.info(business_id) if business_id else {}
    if info.get("name"):
        facts.insert(0, _fact("name", info["name"], "user:signup", "user", 1.0, info.get("updated_at") or at))
    contact = _contact_email(business_id)
    if contact:
        facts.append(_fact("contact_email", contact, "google:signin", "user", 0.9, at))
    if domain:
        facts.append(_fact("website", f"https://{domain}", "user:signup" if business_id else f"https://{domain}", "user" if business_id else "web", 0.9, at))

    email = {"business_id": business_id, "fetched_at": None, "message_count": 0, "categories": {}, "signals": []}
    if business_id:
        messages = store.read_messages(business_id)
        email["fetched_at"] = store.fetched_at(business_id)
        email["message_count"] = len(messages)
        email["categories"] = {c["name"]: c["count"] for c in inbox.summarize(messages)["categories"]}
        found = _email_facts(business_id, messages, email["fetched_at"], use_llm)
        email["llm"] = found["llm"]
        facts += found["facts"]
        email["signals"] = [
            {"key": f["key"], "value": f["value"], "source": f["source"], "date": f.get("message_date")}
            for f in found["facts"] if f["key"] in email_facts.SIGNAL_KEYS
        ]

    business = best_values(facts)
    if not business.get("name"):
        business["name"] = (profile or {}).get("name") or business.get("dba") or business.get("legal_name")
    return {
        "schema": SCHEMA,
        "slug": re.sub(r"[^a-z0-9]+", "-", domain).strip("-") if domain else business_id,
        "domain": domain,
        "generated_at": at,
        "business": business,
        "facts": facts,
        "email": email,
        "credits": _credits(profile, business, domain),
        "missing_info": missing(business, facts),
    }


def profile_facts(profile: dict) -> list[dict]:
    """Company-profile claims as dossier facts: the top claim of single fields, up to 5 of multi fields."""
    from company_research.profile import FIELDS

    out = []
    for name, claims in (profile.get("fields") or {}).items():
        multi = FIELDS.get(name, ("", False))[1]
        if multi:
            chosen = claims[:MULTI_LIMIT]
        else:  # the top claim plus the best claim from each other kind of source, so kind priority can apply
            chosen, kinds_seen = [], set()
            for claim in claims:
                kind = _kind(claim)
                if not chosen or kind not in kinds_seen:
                    chosen.append(claim)
                kinds_seen.add(kind)
        for claim in chosen:
            sources = claim.get("sources") or [{}]
            kinds = [_kind(claim)]
            out.append(_fact(
                ALIASES.get(name, name), claim.get("value"), sources[0].get("url") or sources[0].get("via") or "",
                kinds[0] if kinds else "web", claim.get("confidence", 0.0), sources[0].get("fetched_at") or profile.get("generated_at"),
                via=sources[0].get("via"),
            ))
    return out


def _kind(claim: dict) -> str:
    kinds = sorted({COLLECTOR_KIND.get(c, "web") for c in claim.get("collectors") or []}, key=KIND_RANK.get)
    return kinds[0] if kinds else "web"


def best_values(facts: list[dict]) -> dict:
    business = dict.fromkeys(BUSINESS_KEYS)
    ranked = sorted(facts, key=lambda f: (KIND_RANK.get(f["source_kind"], 9), -float(f.get("confidence") or 0)))
    for f in ranked:
        key = ALIASES.get(f["key"], f["key"])
        if key in business and business[key] is None and f["value"] not in (None, "", []):
            business[key] = f["value"]
    naics = business.get("naics")
    if isinstance(naics, dict):
        business["naics"] = [naics["code"]] if naics.get("code") else []
    elif isinstance(naics, str):
        business["naics"] = [naics]
    else:
        business["naics"] = []
    return business


def missing(business: dict, facts: list[dict]) -> list[str]:
    have = {k for k, v in business.items() if v not in (None, "", [])} | {f["key"] for f in facts if f["value"] not in (None, "")}
    return [f for f in FORM_FIELDS if f not in have]


def mask_ein(value) -> str:
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return f"••-•••{digits[-4:]}" if len(digits) >= 4 else "••-•••••••"


def _email_facts(business_id: str, messages: list[dict], fetched_at: str | None, use_llm: bool) -> dict:
    """Email facts, cached per fetch (the LLM pass is slow): data/<id>/email_facts.json."""
    path = company.business_dir(business_id) / "email_facts.json"
    cached = _read_json(path)
    if cached and cached.get("fetched_at") == fetched_at and (cached.get("llm") == "ok" or not use_llm):
        return cached
    found = email_facts.extract(messages, use_llm=use_llm)
    if messages:
        company._write(path, {"fetched_at": fetched_at, **found})
    return found


def _credits(profile: dict | None, business: dict, domain: str | None) -> list[dict]:
    try:
        catalog = legal_store.read_catalog()
    except (OSError, ValueError):
        return []
    if not catalog:
        return []
    if not profile:  # match on what we know without public research
        best = {k: v for k, v in {"industry": business.get("industry"), "hq_address": business.get("hq_address")}.items() if v}
        profile = {"domain": domain, "best": best, "fields": {}}
    return match_programs(profile, catalog)


def _contact_email(business_id: str | None) -> str | None:
    if not business_id:
        return None
    try:
        from .gmail import auth

        return auth.get(business_id).email
    except Exception:
        return None


def _fact(key, value, source, kind, confidence, captured_at, via=None) -> dict:
    fact = {"key": key, "value": value, "source": source, "source_kind": kind, "confidence": round(float(confidence or 0), 2),
            "captured_at": captured_at}
    if via:
        fact["via"] = via
    return fact


def _read_profile(out_dir: Path) -> dict | None:
    try:
        return company_store.read_profile(out_dir)
    except (OSError, ValueError):
        return None


def _read_json(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")
