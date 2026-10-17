"""Shared dossier → search-profile / opportunity contract for the unified Wallet."""

from __future__ import annotations

import os
import re
from typing import Any

OPPORTUNITY_UNCLAIMED = "unclaimed_property"
OPPORTUNITY_TAX_CREDIT = "tax_credit"

_ADDRESS_RE = re.compile(
    r"^(?P<street>.+?),\s*(?P<city>[^,]+?),\s*(?P<state>[A-Z]{2})\.?\s+(?P<zip>\d{5})(?:-\d{4})?"
    r"(?:\s*,\s*(?:USA?|United States))?\s*$"
)


def dossier_to_search_profile(
    dossier: dict[str, Any],
    *,
    business_id: str,
    consent: bool = True,
) -> dict[str, Any]:
    """Normalize a moneyfinder.dossier/v1 (or company profile) into the B2B search shape."""
    business = dict(dossier.get("business") or {})
    facts = dossier.get("facts") or []
    slug = dossier.get("slug") or business_id

    legal_name = business.get("legal_name") or business.get("name") or ""
    dba = business.get("dba")
    address = _parse_address(business.get("hq_address") or "")
    officer_name = business.get("officer_name") or _fact_value(facts, "officer_name") or ""
    officer_title = business.get("officer_title") or _fact_value(facts, "officer_title") or ""

    return {
        "id": business_id,
        "business_id": business_id,
        "dossier_slug": slug,
        "entity_type": "business",
        "legal_name": str(legal_name),
        "dbas": [dba] if dba else [],
        "business_type": business.get("entity_type"),
        "addresses": [
            {
                "street": address.get("street") or business.get("hq_address") or "",
                "city": address.get("city") or business.get("nyc_borough") or "",
                "state": address.get("state") or "NY",
                "zip": address.get("zip") or "",
                "current": True,
                "source": _source_for(facts, "hq_address", business.get("hq_address")),
            }
        ],
        "authorized_representative": {
            "name": str(officer_name),
            "role": str(officer_title),
            "source": _source_for(facts, "officer_name", officer_name) or "user",
            "requires_confirmation": not bool(officer_name),
        },
        "search_consent": bool(consent),
        "research_source": dossier.get("domain"),
        "dataset_release": os.environ.get("NY_DATA_RELEASE", "local"),
        "demo": bool(dossier.get("demo")),
    }


def credit_to_opportunity(credit: dict[str, Any], *, business_id: str, slug: str) -> dict[str, Any]:
    """Shape a matched tax-credit program as a Wallet opportunity (not a claim yet)."""
    forms = credit.get("forms") or []
    return {
        "opportunity_type": OPPORTUNITY_TAX_CREDIT,
        "business_id": business_id,
        "dossier_slug": slug,
        "id": f"credit:{credit.get('id') or credit.get('name')}",
        "title": credit.get("name") or "Tax credit",
        "program_id": credit.get("id"),
        "jurisdiction": credit.get("jurisdiction"),
        "status_hint": credit.get("status") or "possible",
        "confidence": credit.get("score") or credit.get("confidence"),
        "reasons": list(credit.get("why") or credit.get("reasons") or []),
        "forms": forms,
        "amount_cents": None,
        "amount_status": "estimate_unavailable",
        "source": "legal_catalog",
        "source_mode": "catalog",
        "demo_only": False,
        "next_action": "Review credit form" if forms else "Open program page",
    }


def hit_to_opportunity(hit: dict[str, Any], *, business_id: str, slug: str, source_mode: str) -> dict[str, Any]:
    """Shape an unclaimed-property search hit as a Wallet opportunity."""
    source = str(hit.get("source") or "unknown")
    demo_only = source.startswith(("mock_", "demo:")) or source_mode in {"demo", "demo_only"}
    amount = hit.get("amount_cents")
    return {
        "opportunity_type": OPPORTUNITY_UNCLAIMED,
        "business_id": business_id,
        "dossier_slug": slug,
        "id": f"unclaimed:{source}:{hit.get('found_name')}:{hit.get('zip')}:{amount}",
        "title": hit.get("found_name") or "Unclaimed property match",
        "property_type": hit.get("property_type"),
        "city": hit.get("city"),
        "zip": hit.get("zip"),
        "amount_cents": amount,
        "amount_status": "disclosed" if amount is not None else "not_disclosed",
        "confidence": hit.get("confidence"),
        "reasons": list(hit.get("reasons") or []),
        "hit": hit,
        "source": source,
        "source_mode": source_mode,
        "demo_only": demo_only,
        "next_action": "Prepare claim form",
    }


def _parse_address(raw: str) -> dict[str, str]:
    match = _ADDRESS_RE.match((raw or "").strip())
    if not match:
        return {}
    return {k: (match[k] or "").strip() for k in ("street", "city", "state", "zip")}


def _fact_value(facts: list[dict[str, Any]], key: str) -> Any:
    for fact in facts:
        if fact.get("key") == key and fact.get("value") not in (None, ""):
            return fact.get("value")
    return None


def _source_for(facts: list[dict[str, Any]], key: str, value: Any) -> str:
    for fact in facts:
        if fact.get("key") == key and (value in (None, "") or fact.get("value") == value):
            return str(fact.get("source_kind") or fact.get("source") or "dossier")
    return "dossier"
