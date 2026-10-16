#!/usr/bin/env python3
"""Integration path: profile → match → form fix → approve → submit → agency → bank."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.agent.tools import AgentToolbox
from src.forms.provenance import FormField, form_hash, validate_fields
from src.pipeline.status import can_transition


def test_end_to_end_synthetic() -> None:
    box = AgentToolbox()
    profile = box.build_search_profile(
        {
            "entity_type": "business",
            "legal_name": "Example NYC Foods LLC",
            "dbas": ["Example Foods"],
            "addresses": [{"city": "Brooklyn", "state": "NY", "zip": "11201", "current": True}],
            "authorized_representative": {"name": "Maria Alvarez", "role": "Managing Member"},
            "search_consent": True,
        }
    )
    variants = box.generate_name_variants(profile)
    assert "Example NYC Foods LLC" in variants or any("Example" in v for v in variants)

    hits = box.search_unclaimed(profile)
    assert hits, "expected at least one mock hit"

    prepared = box.prepare_claim_form(profile, hits[0])
    fields = [FormField(**f) for f in prepared["fields"]]
    # User resolves conflicts
    for f in fields:
        if f.requires_confirmation:
            f.value = "11201"
            f.requires_confirmation = False
            f.edited_by_user = True
            f.source = "edited_by_user"
    assert not validate_fields(fields)
    fh = form_hash(fields)
    approval = box.request_user_approval(fh, True)
    assert approval["status"] == "USER_APPROVED"

    readback = {f.field: f.value for f in fields}
    submitted = box.daytona_fill_and_submit(
        approved_fields=[f.__dict__ for f in fields],
        browser_readback=readback,
        claim_id="claim_demo_001",
    )
    assert submitted["ok"]
    assert submitted["status"] == "CLAIM_RECEIVED"
    assert can_transition("SUBMITTED", "CLAIM_RECEIVED", "agency_receipt").ok

    conf = submitted["confirmation_id"]
    st = box.poll_agency_status(conf, advance=True)
    assert st["status"] in {"PROCESSING", "APPROVED", "PAYMENT_ISSUED", "CLAIM_RECEIVED"}

    # Advance until payment issued
    for _ in range(4):
        st = box.poll_agency_status(conf, advance=True)
        if st["status"] == "PAYMENT_ISSUED":
            break
    assert st["status"] == "PAYMENT_ISSUED"
    assert can_transition("APPROVED", "PAYMENT_ISSUED", "agency_payment_issued").ok

    bank = box.match_bank_transaction(
        "acct_demo",
        amount_cents=hits[0]["amount_cents"],
        confirmation_id=conf,
        emit_demo_deposit=True,
    )
    assert bank["matched"]
    assert bank["transaction"]["synthetic"] is True
    assert can_transition("PAYMENT_ISSUED", "PAYMENT_CONFIRMED", "bank_deposit").ok


def test_illegal_skip_blocked() -> None:
    assert not can_transition("MATCH_FOUND", "PAYMENT_CONFIRMED", "bank_deposit").ok


if __name__ == "__main__":
    test_end_to_end_synthetic()
    test_illegal_skip_blocked()
    print("All integration checks passed.")
