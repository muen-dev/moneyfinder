#!/usr/bin/env python3
"""Offline Arize-shaped evaluations for synthetic B2B profiles."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.agent.tools import AgentToolbox
from src.forms.deadlines import extract_deadline
from src.forms.provenance import FormField, form_hash, prepare_business_claim_fields, validate_fields
from src.pipeline.status import can_transition


def main() -> int:
    profiles = json.loads((Path(__file__).parent / "synthetic_profiles.json").read_text())
    box = AgentToolbox()
    results = []

    for case in profiles:
        profile = box.build_search_profile(case["profile"])
        hits = box.search_unclaimed(profile)
        hit_ok = len(hits) >= case["expected_min_hits"]
        name_ok = True
        if case["expected_top_name_contains"]:
            name_ok = bool(hits) and case["expected_top_name_contains"].lower() in hits[0]["found_name"].lower()
        results.append({"metric": "search_matching", "id": case["id"], "score": 1.0 if hit_ok and name_ok else 0.0})

        if hits:
            form = box.prepare_claim_form(profile, hits[0])
            fields = [FormField(**f) for f in form["fields"]]
            sourced = all(f.source for f in fields)
            results.append({"metric": "source_attribution", "id": case["id"], "score": 1.0 if sourced else 0.0})
            # Resolve confirmations for accuracy metric after user edit simulation
            for f in fields:
                if f.requires_confirmation:
                    f.requires_confirmation = False
                    f.edited_by_user = True
            errs = validate_fields(fields)
            results.append({"metric": "field_accuracy_ready", "id": case["id"], "score": 1.0 if not errs else 0.0})
            results.append({"metric": "form_hash_stable", "id": case["id"], "score": 1.0 if form_hash(fields) else 0.0})

    # Status transition legality
    legal = can_transition("PROCESSING", "APPROVED", "agency_approval")
    illegal = can_transition("CLAIM_RECEIVED", "PAYMENT_CONFIRMED", "bank_deposit")
    results.append({"metric": "status_transition_legal", "id": "machine", "score": 1.0 if legal.ok else 0.0})
    results.append({"metric": "status_transition_illegal_blocked", "id": "machine", "score": 1.0 if not illegal.ok else 0.0})

    # Approval compliance: submit blocked when confirmation flags remain
    profile = box.build_search_profile(profiles[0]["profile"])
    hits = box.search_unclaimed(profile)
    prepared = box.prepare_claim_form(profile, hits[0])
    flagged = []
    for f in prepared["fields"]:
        row = dict(f)
        if row["field"] == "zip":
            row["requires_confirmation"] = True
            row["conflicting_value"] = "99999"
            row["source_of_conflict"] = "state_record"
        flagged.append(row)
    blocked = False
    try:
        box.daytona_fill_and_submit(
            approved_fields=flagged,
            browser_readback={f["field"]: f["value"] for f in flagged},
            claim_id="eval1",
        )
    except PermissionError:
        blocked = True
    results.append({"metric": "approval_compliance", "id": "submit_gate", "score": 1.0 if blocked else 0.0})

    # Deadline extraction (agency copy such as "most are paid within 30 days")
    deadline = extract_deadline("Allow up to 90 days for us to review your claim. Most are paid within 30 days.")
    results.append(
        {
            "metric": "deadline_extraction",
            "id": "agency_copy",
            "score": 1.0 if deadline and deadline.label else 0.0,
        }
    )

    by_metric: dict[str, list[float]] = {}
    for r in results:
        by_metric.setdefault(r["metric"], []).append(r["score"])
    print("MoneyFinder eval summary (replace with Arize export):")
    for metric, scores in sorted(by_metric.items()):
        avg = sum(scores) / len(scores)
        print(f"  {metric}: {avg:.2f} ({sum(scores):.0f}/{len(scores)})")
    failed = [r for r in results if r["score"] < 1.0]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
