"""Imported New York unclaimed-property adapter.

The state/location-provider export is intentionally treated as an input file:
the application never pretends that a bundled demo corpus is government data.
Supported formats are JSON array and delimited text with a header row.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .adapter import SearchHit
from .scoring import score_match
from .variants import address_refinements, generate_name_variants


class ImportedNYUnclaimedAdapter:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        if not self.path.is_file():
            raise FileNotFoundError(f"NY unclaimed-funds data file not found: {self.path}")

    def _rows(self) -> list[dict[str, Any]]:
        if self.path.suffix.lower() == ".json":
            value = json.loads(self.path.read_text())
            if not isinstance(value, list):
                raise ValueError("NY data JSON must be an array")
            return [dict(row) for row in value]
        with self.path.open(newline="", encoding="utf-8-sig") as fh:
            return [dict(row) for row in csv.DictReader(fh, delimiter="\t")]

    def search(self, profile: dict) -> list[SearchHit]:
        names = generate_name_variants(profile["legal_name"], profile.get("dbas") or [])
        refinements = address_refinements(profile.get("addresses") or [])
        primary = refinements[0] if refinements else {"city": None, "zip": None}
        results: list[SearchHit] = []
        for row in self._rows():
            found_name = str(row.get("found_name") or row.get("name") or row.get("business_name") or "")
            if not found_name:
                continue
            city = str(row.get("city") or "")
            zip_code = str(row.get("zip") or row.get("zipcode") or "")
            score = score_match(
                query_names=names,
                found_name=found_name,
                query_city=primary.get("city"),
                found_city=city,
                query_zip=primary.get("zip"),
                found_zip=zip_code,
            )
            if score.confidence < 0.35:
                continue
            raw_amount = row.get("amount_cents") or row.get("amount")
            try:
                amount_cents = int(float(raw_amount) * 100) if raw_amount is not None else None
            except (TypeError, ValueError):
                amount_cents = None
            results.append(
                SearchHit(
                    found_name=found_name,
                    property_type=str(row.get("property_type") or row.get("property") or "Unclaimed property"),
                    city=city,
                    zip=zip_code,
                    amount_cents=amount_cents,
                    source=str(row.get("source") or f"import:{self.path.name}"),
                    confidence=score.confidence,
                    reasons=score.reasons,
                )
            )
        return sorted(results, key=lambda item: item.confidence, reverse=True)


def hits_as_dict(hits: list[SearchHit]) -> list[dict[str, Any]]:
    return [asdict(hit) for hit in hits]
