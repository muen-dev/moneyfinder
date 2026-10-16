"""Map sourced company-research output into the shared B2B search profile."""

from __future__ import annotations

from typing import Any


def _best(fields: dict[str, list[dict[str, Any]]], key: str) -> Any:
    values = fields.get(key) or []
    return values[0].get("value") if values else None


def company_profile_to_search_profile(profile: dict[str, Any], *, consent: bool) -> dict[str, Any]:
    """Convert research/company profile.json into contracts/b2b_input.schema.json shape."""
    best = profile.get("best") or {}
    fields = profile.get("fields") or {}
    legal_name = best.get("legal_name") or _best(fields, "legal_name") or profile.get("domain", "")
    address = best.get("hq_address") or _best(fields, "hq_address") or ""
    city = best.get("city") or _best(fields, "city") or ""
    zip_code = best.get("zip") or _best(fields, "zip") or ""
    state = best.get("state") or _best(fields, "state") or "NY"

    representative = best.get("authorized_representative") or profile.get("authorized_representative") or {}
    return {
        "entity_type": "business",
        "legal_name": str(legal_name),
        "dbas": list(profile.get("dbas") or best.get("dbas") or []),
        "business_type": best.get("entity_type") or _best(fields, "entity_type"),
        "addresses": [
            {
                "street": str(address),
                "city": str(city),
                "state": str(state),
                "zip": str(zip_code),
                "current": True,
                "source": "company_research",
            }
        ],
        "authorized_representative": {
            "name": str(representative.get("name") or ""),
            "role": str(representative.get("role") or ""),
            "source": "user_input",
            "requires_confirmation": not bool(representative.get("name")),
        },
        "search_consent": consent,
        "research_source": profile.get("domain"),
        "research_facts": fields,
    }
