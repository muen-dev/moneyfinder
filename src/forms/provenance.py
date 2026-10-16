"""Field provenance, conflicts, validation, and form hashing."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass


@dataclass
class FormField:
    field: str
    value: str
    source: str
    confidence: float = 1.0
    requires_confirmation: bool = False
    conflicting_value: str | None = None
    source_of_conflict: str | None = None
    edited_by_user: bool = False


def prepare_business_claim_fields(profile: dict, hit: dict) -> list[FormField]:
    """Build claim fields with intentional ZIP conflict when demo records disagree."""
    addr = next((a for a in profile.get("addresses", []) if a.get("current")), None)
    addr = addr or (profile.get("addresses") or [{}])[0]
    user_zip = (addr.get("zip") or "")[:5]
    record_zip = (hit.get("zip") or "")[:5]

    fields = [
        FormField("legal_name", profile["legal_name"], "user_input", 0.99),
        FormField(
            "authorized_representative",
            profile["authorized_representative"]["name"],
            "user_input",
            0.98,
        ),
        FormField("role", profile["authorized_representative"]["role"], "user_input", 0.98),
        FormField("city", addr.get("city", ""), "user_input", 0.95),
        FormField(
            "amount_requested",
            f"${(hit.get('amount_cents') or 0) / 100:.2f}",
            "search_result",
            0.9,
        ),
        FormField("property_name", hit.get("found_name", ""), "search_result", 0.92),
        FormField("pay_to", "Business demo account ••4821", "user_account", 0.9),
    ]

    zip_field = FormField("zip", record_zip or user_zip, "state_record", 0.85)
    if user_zip and record_zip and user_zip != record_zip:
        # Prefer showing user-entered ZIP as value needing confirmation against state record.
        zip_field = FormField(
            field="zip",
            value=user_zip,
            source="user_input",
            confidence=0.7,
            requires_confirmation=True,
            conflicting_value=record_zip,
            source_of_conflict="state_record",
        )
    fields.insert(4, zip_field)
    return fields


def validate_fields(fields: list[FormField]) -> list[str]:
    errors: list[str] = []
    required = {"legal_name", "authorized_representative", "zip", "city"}
    present = {f.field for f in fields if f.value.strip()}
    for key in required:
        if key not in present:
            errors.append(f"Missing required field: {key}")
    for f in fields:
        if f.requires_confirmation:
            errors.append(f"Field requires confirmation: {f.field}")
    return errors


def form_hash(fields: list[FormField]) -> str:
    payload = [{k: v for k, v in asdict(f).items()} for f in sorted(fields, key=lambda x: x.field)]
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def readback_diff(approved: list[FormField], entered: dict[str, str]) -> list[str]:
    """Compare browser read-back values to approved snapshot."""
    mismatches: list[str] = []
    for f in approved:
        got = entered.get(f.field)
        if got is None:
            mismatches.append(f"Missing in browser: {f.field}")
        elif got.strip() != f.value.strip():
            mismatches.append(f"Mismatch {f.field}: approved={f.value!r} browser={got!r}")
    return mismatches
