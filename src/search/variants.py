"""Generate NY unclaimed-funds search name variants from a B2B profile."""

from __future__ import annotations

import re
from typing import Iterable

_SUFFIXES = re.compile(
    r"\b(llc|l\.l\.c\.|inc|incorporated|corp|corporation|co|company|ltd|limited|pllc|lp|llp)\b\.?",
    re.IGNORECASE,
)
_PUNCT = re.compile(r"[^\w\s&]", re.UNICODE)
_SPACE = re.compile(r"\s+")


def normalize_name(name: str) -> str:
    cleaned = _PUNCT.sub(" ", name.strip())
    cleaned = _SPACE.sub(" ", cleaned).strip()
    return cleaned


def strip_entity_suffix(name: str) -> str:
    return _SPACE.sub(" ", _SUFFIXES.sub("", normalize_name(name))).strip()


def generate_name_variants(legal_name: str, dbas: Iterable[str] | None = None) -> list[str]:
    """Return ordered unique search strings for NY business-name search."""
    seen: set[str] = set()
    out: list[str] = []

    def add(raw: str) -> None:
        for candidate in (normalize_name(raw), strip_entity_suffix(raw)):
            key = candidate.casefold()
            if candidate and key not in seen:
                seen.add(key)
                out.append(candidate)

    add(legal_name)
    for dba in dbas or []:
        add(dba)
    return out


def address_refinements(addresses: list[dict]) -> list[dict]:
    """City/ZIP pairs used to refine NY search."""
    refinements: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for addr in addresses:
        city = (addr.get("city") or "").strip()
        zip_code = (addr.get("zip") or "").strip()[:5]
        key = (city.casefold(), zip_code)
        if city and zip_code and key not in seen:
            seen.add(key)
            refinements.append({"city": city, "zip": zip_code})
    return refinements
