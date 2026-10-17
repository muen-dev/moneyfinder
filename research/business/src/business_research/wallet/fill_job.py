"""Approval-gated form fill jobs: build Anchor plans and receipts; never auto-submit."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from . import _repo

_repo.ensure_repo_on_path()

from src.forms.provenance import FormField, form_hash, readback_diff  # noqa: E402
from src.persistence import now_iso  # noqa: E402


def plan_from_approved_form(form: dict[str, Any]) -> dict[str, Any]:
    """Immutable snapshot for browser fill: only non-confirmation fields with values."""
    fields = [FormField(**f) if isinstance(f, dict) else f for f in form.get("fields") or []]
    approved = []
    needs_user = []
    for field in fields:
        if field.requires_confirmation:
            needs_user.append({"field": field.field, "reason": "requires_confirmation"})
            continue
        if not (field.value or "").strip():
            needs_user.append({"field": field.field, "reason": "empty"})
            continue
        approved.append(
            {
                "field": field.field,
                "value": field.value,
                "source": field.source,
                "confidence": field.confidence,
            }
        )
    snapshot = {
        "schema": "moneyfinder.approved_form_snapshot/v1",
        "claim_id": form.get("claim_id"),
        "form_hash": form.get("form_hash") or form_hash(fields),
        "approved": bool(form.get("approved")),
        "fields": approved,
        "needs_user": needs_user,
        "created_at": now_iso(),
        "submit": False,
    }
    return snapshot


def simulate_fill(snapshot: dict[str, Any], *, mode: str = "mock_portal") -> dict[str, Any]:
    """Deterministic fill receipt for tests and offline demos (no live Anchor session).

    Live Anchor is opt-in via WALLET_LIVE_ANCHOR=1 and is never invoked from the default path.
    """
    if not snapshot.get("approved"):
        raise PermissionError("Cannot fill without an approved form snapshot")
    if snapshot.get("submit"):
        raise PermissionError("Auto-submit is forbidden; stop at ready_for_user_submission")

    filled = {row["field"]: row["value"] for row in snapshot.get("fields") or []}
    # Perfect readback in simulate mode.
    mismatches = readback_diff(
        [FormField(field=k, value=v, source="approved") for k, v in filled.items()],
        filled,
    )
    status = "browser_mismatch" if mismatches else "ready_for_user_submission"
    return {
        "schema": "moneyfinder.form_fill_receipt/v1",
        "mode": mode,
        "live_anchor": False,
        "status": status,
        "submitted": False,
        "filled": {k: {"value": v, "source": "approved_snapshot"} for k, v in filled.items()},
        "needs_user": list(snapshot.get("needs_user") or []),
        "mismatches": mismatches,
        "form_hash": snapshot.get("form_hash"),
        "claim_id": snapshot.get("claim_id"),
        "created_at": now_iso(),
        "note": "Simulated fill. Set WALLET_LIVE_ANCHOR=1 to use Anchor Browser.",
    }


def write_receipt(path: Path, receipt: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2) + "\n")
    return path


def live_anchor_enabled() -> bool:
    return os.environ.get("WALLET_LIVE_ANCHOR", "").strip() == "1"
