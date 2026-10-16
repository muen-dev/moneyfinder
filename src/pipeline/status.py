"""Claim status machine with evidence gates."""

from __future__ import annotations

from dataclasses import dataclass

ALLOWED: dict[str, set[str]] = {
    "MATCH_FOUND": {"FORM_READY", "STOPPED_BY_USER"},
    "FORM_READY": {"USER_APPROVED", "MATCH_FOUND", "STOPPED_BY_USER"},
    "USER_APPROVED": {"SUBMITTED", "FORM_READY", "STOPPED_BY_USER"},
    "SUBMITTED": {"CLAIM_RECEIVED", "STOPPED_BY_USER"},
    "CLAIM_RECEIVED": {"PROCESSING", "NEEDS_DOCS", "REJECTED"},
    "PROCESSING": {"APPROVED", "NEEDS_DOCS", "REJECTED", "PROCESSING"},
    "NEEDS_DOCS": {"PROCESSING", "FORM_READY", "STOPPED_BY_USER"},
    "APPROVED": {"PAYMENT_ISSUED", "PROCESSING"},
    "PAYMENT_ISSUED": {"PAYMENT_CONFIRMED"},
    "PAYMENT_CONFIRMED": set(),
    "REJECTED": set(),
    "STOPPED_BY_USER": set(),
}

EVIDENCE_REQUIRED: dict[str, str] = {
    "SUBMITTED": "submission",
    "CLAIM_RECEIVED": "agency_receipt",
    "APPROVED": "agency_approval",
    "PAYMENT_ISSUED": "agency_payment_issued",
    "PAYMENT_CONFIRMED": "bank_deposit",
}


@dataclass
class TransitionResult:
    ok: bool
    error: str | None = None


def can_transition(from_status: str, to_status: str, evidence_kind: str | None) -> TransitionResult:
    allowed = ALLOWED.get(from_status, set())
    if to_status not in allowed:
        return TransitionResult(False, f"Illegal transition {from_status} → {to_status}")
    required = EVIDENCE_REQUIRED.get(to_status)
    if required and evidence_kind != required:
        return TransitionResult(
            False,
            f"Transition to {to_status} requires evidence kind '{required}', got '{evidence_kind}'",
        )
    return TransitionResult(True)
