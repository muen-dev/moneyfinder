"""Tests for domain-first profile mapping and imported money data."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.profile_mapper import company_profile_to_search_profile
from src.search.imported import ImportedNYUnclaimedAdapter


def test_company_profile_maps_to_search_profile() -> None:
    result = company_profile_to_search_profile(
        {
            "domain": "example.com",
            "best": {
                "legal_name": "Example Foods LLC",
                "hq_address": "123 Main Street",
                "city": "Brooklyn",
                "state": "NY",
                "zip": "11201",
                "entity_type": "LLC",
                "authorized_representative": {"name": "Maria", "role": "Member"},
            },
            "fields": {},
        },
        consent=True,
    )
    assert result["legal_name"] == "Example Foods LLC"
    assert result["addresses"][0]["zip"] == "11201"
    assert result["authorized_representative"]["name"] == "Maria"


def test_imported_adapter_reads_json(tmp_path: Path) -> None:
    path = tmp_path / "ny.json"
    path.write_text(
        json.dumps(
            [
                {
                    "name": "Example Foods",
                    "property_type": "Uncashed check",
                    "city": "Brooklyn",
                    "zip": "11201",
                    "amount": 412,
                    "source": "test-import",
                }
            ]
        )
    )
    hits = ImportedNYUnclaimedAdapter(path).search(
        {
            "legal_name": "Example Foods LLC",
            "dbas": [],
            "addresses": [{"city": "Brooklyn", "zip": "11201"}],
        }
    )
    assert len(hits) == 1
    assert hits[0].amount_cents == 41200
    assert hits[0].source == "test-import"
