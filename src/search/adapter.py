"""Search adapters: mock for demo, hook for real NY later."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Protocol

from .scoring import score_match
from .variants import address_refinements, generate_name_variants


@dataclass
class SearchHit:
    found_name: str
    property_type: str
    city: str
    zip: str
    amount_cents: int | None
    source: str
    confidence: float
    reasons: list[str]


class UnclaimedSearchAdapter(Protocol):
    def search(self, profile: dict) -> list[SearchHit]: ...


# Synthetic NY-like corpus for hackathon (not real state data).
_MOCK_CORPUS = [
    {
        "found_name": "Example Foods",
        "property_type": "Uncashed vendor check",
        "city": "Brooklyn",
        "zip": "11201",
        "amount_cents": 41200,
        "source": "mock_ny_unclaimed",
    },
    {
        "found_name": "Example NYC Foods LLC",
        "property_type": "Utility deposit refund",
        "city": "Brooklyn",
        "zip": "11201",
        "amount_cents": 18500,
        "source": "mock_ny_unclaimed",
    },
    {
        "found_name": "Example NYC Market",
        "property_type": "Accounts payable credit",
        "city": "Queens",
        "zip": "11101",
        "amount_cents": 9750,
        "source": "mock_ny_unclaimed",
    },
]


class MockNYUnclaimedAdapter:
    def search(self, profile: dict) -> list[SearchHit]:
        names = generate_name_variants(profile["legal_name"], profile.get("dbas") or [])
        refinements = address_refinements(profile.get("addresses") or [])
        primary = refinements[0] if refinements else {"city": None, "zip": None}
        hits: list[SearchHit] = []
        for row in _MOCK_CORPUS:
            scored = score_match(
                query_names=names,
                found_name=row["found_name"],
                query_city=primary.get("city"),
                found_city=row["city"],
                query_zip=primary.get("zip"),
                found_zip=row["zip"],
            )
            if scored.confidence < 0.35:
                continue
            hits.append(
                SearchHit(
                    found_name=row["found_name"],
                    property_type=row["property_type"],
                    city=row["city"],
                    zip=row["zip"],
                    amount_cents=row["amount_cents"],
                    source=row["source"],
                    confidence=scored.confidence,
                    reasons=scored.reasons,
                )
            )
        return sorted(hits, key=lambda h: h.confidence, reverse=True)


def configured_adapter():
    """Use imported state data when configured; otherwise return explicit demo adapter."""
    data_file = os.environ.get("NY_UNCLAIMED_DATA_FILE", "").strip()
    if data_file:
        from .imported import ImportedNYUnclaimedAdapter

        return ImportedNYUnclaimedAdapter(data_file)
    return MockNYUnclaimedAdapter()
