"""Persistence boundary: JSON fallback now, SurrealDB-shaped records for future mapping."""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .pipeline.status import can_transition


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


STATUS_PROGRESS = {
    "MATCH_FOUND": 10,
    "FORM_READY": 20,
    "USER_APPROVED": 30,
    "SUBMITTED": 40,
    "CLAIM_RECEIVED": 50,
    "PROCESSING": 60,
    "NEEDS_DOCS": 55,
    "APPROVED": 75,
    "PAYMENT_ISSUED": 90,
    "PAYMENT_CONFIRMED": 100,
    "REJECTED": 0,
    "STOPPED_BY_USER": 0,
}

EVIDENCE_FOR_STATUS = {
    "SUBMITTED": "submission",
    "CLAIM_RECEIVED": "agency_receipt",
    "APPROVED": "agency_approval",
    "PAYMENT_ISSUED": "agency_payment_issued",
    "PAYMENT_CONFIRMED": "bank_deposit",
}


class EventRepository:
    def save_profile(self, profile: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def append_event(self, event: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def events(self, claim_id: str | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError

    def create_claim(self, claim: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def update_claim(self, claim_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def get_claim(self, claim_id: str) -> dict[str, Any] | None:
        raise NotImplementedError

    def claims(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    def save_form(self, form: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def get_form(self, claim_id: str) -> dict[str, Any] | None:
        raise NotImplementedError

    def append_evidence(self, evidence: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def evidence(self, claim_id: str | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError

    def transition_claim(
        self,
        *,
        claim_id: str,
        to_status: str,
        actor: str,
        evidence_kind: str | None = None,
        source: str = "local_demo",
        reference: str | None = None,
        note: str | None = None,
        payload: dict[str, Any] | None = None,
        claim_updates: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError

    def tracker(self) -> dict[str, Any]:
        raise NotImplementedError

    def reset_demo(self, seed: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class JsonEventRepository(EventRepository):
    """Local development repository with the same event shape as Surreal schema."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path or os.environ.get("MONEYFINDER_EVENT_FILE", "data/moneyfinder-events.json"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        if not self.path.exists():
            self._write(self._empty())

    @staticmethod
    def _empty() -> dict[str, Any]:
        return {
            "profiles": [],
            "claims": [],
            "forms": [],
            "events": [],
            "evidence": [],
            "memory_trail": [],
            "meta": {"schema_version": 2, "persistence": "json", "surreal_ready": True},
        }

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._empty()
        data = json.loads(self.path.read_text())
        for key in ("profiles", "claims", "forms", "events", "evidence", "memory_trail"):
            data.setdefault(key, [])
        data.setdefault("meta", {"schema_version": 2, "persistence": "json", "surreal_ready": True})
        return data

    def _write(self, value: dict[str, Any]) -> None:
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(value, indent=2, default=str))
        temp.replace(self.path)

    def save_profile(self, profile: dict[str, Any]) -> dict[str, Any]:
        record = {**profile, "id": profile.get("id") or new_id("biz"), "saved_at": now_iso()}
        with self._lock:
            data = self._read()
            data["profiles"].append(record)
            self._write(data)
        return record

    def append_event(self, event: dict[str, Any]) -> dict[str, Any]:
        record = {**event, "id": event.get("id") or new_id("evt"), "created_at": event.get("created_at") or now_iso()}
        with self._lock:
            data = self._read()
            data["events"].append(record)
            if record.get("claim_id") and record.get("to_status"):
                for claim in data["claims"]:
                    if claim.get("id") == record["claim_id"] or claim.get("claim_id") == record["claim_id"]:
                        claim["status"] = record["to_status"]
                        claim["updated_at"] = record["created_at"]
                        claim["progress_pct"] = STATUS_PROGRESS.get(record["to_status"], claim.get("progress_pct", 0))
            self._write(data)
        return record

    def events(self, claim_id: str | None = None) -> list[dict[str, Any]]:
        values = self._read()["events"]
        return [event for event in values if not claim_id or event.get("claim_id") == claim_id]

    def create_claim(self, claim: dict[str, Any]) -> dict[str, Any]:
        claim_id = claim.get("id") or claim.get("claim_id") or new_id("claim")
        status = claim.get("status") or "MATCH_FOUND"
        record = {
            "id": claim_id,
            "claim_id": claim_id,
            "business_id": claim.get("business_id"),
            "business_name": claim.get("business_name"),
            "match_name": claim.get("match_name"),
            "property_type": claim.get("property_type"),
            "city": claim.get("city"),
            "zip": claim.get("zip"),
            "amount_cents": claim.get("amount_cents"),
            "amount_type": claim.get("amount_type", "matched_estimate"),
            "confidence": claim.get("confidence"),
            "status": status,
            "progress_pct": STATUS_PROGRESS.get(status, 0),
            "confirmation_id": claim.get("confirmation_id"),
            "form_hash": claim.get("form_hash"),
            "hit": claim.get("hit"),
            "profile": claim.get("profile"),
            "demo_only": claim.get("demo_only", True),
            "created_at": claim.get("created_at") or now_iso(),
            "updated_at": now_iso(),
            "submitted_at": claim.get("submitted_at"),
            "approved_at": claim.get("approved_at"),
            "payment_issued_at": claim.get("payment_issued_at"),
            "payment_confirmed_at": claim.get("payment_confirmed_at"),
            "last_checked_at": claim.get("last_checked_at"),
            "expected_by": claim.get("expected_by"),
            "next_action": claim.get("next_action", "Prepare claim form"),
        }
        with self._lock:
            data = self._read()
            data["claims"].append(record)
            data["events"].append(
                {
                    "id": new_id("evt"),
                    "claim_id": claim_id,
                    "from_status": None,
                    "to_status": status,
                    "actor": claim.get("actor", "system"),
                    "evidence_kind": None,
                    "source": claim.get("source", "search"),
                    "note": "Claim created from match",
                    "created_at": now_iso(),
                }
            )
            self._write(data)
        return record

    def update_claim(self, claim_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            data = self._read()
            for claim in data["claims"]:
                if claim.get("id") == claim_id or claim.get("claim_id") == claim_id:
                    claim.update(updates)
                    claim["updated_at"] = now_iso()
                    if "status" in updates:
                        claim["progress_pct"] = STATUS_PROGRESS.get(updates["status"], claim.get("progress_pct", 0))
                    self._write(data)
                    return claim
        raise KeyError(f"Unknown claim: {claim_id}")

    def get_claim(self, claim_id: str) -> dict[str, Any] | None:
        for claim in self._read()["claims"]:
            if claim.get("id") == claim_id or claim.get("claim_id") == claim_id:
                return claim
        return None

    def claims(self) -> list[dict[str, Any]]:
        return list(self._read()["claims"])

    def save_form(self, form: dict[str, Any]) -> dict[str, Any]:
        claim_id = form["claim_id"]
        record = {
            **form,
            "id": form.get("id") or new_id("form"),
            "updated_at": now_iso(),
            "created_at": form.get("created_at") or now_iso(),
        }
        with self._lock:
            data = self._read()
            data["forms"] = [f for f in data["forms"] if f.get("claim_id") != claim_id]
            data["forms"].append(record)
            for claim in data["claims"]:
                if claim.get("id") == claim_id or claim.get("claim_id") == claim_id:
                    claim["form_hash"] = record.get("form_hash")
                    # Form saves may mark FORM_READY, but approval/payment statuses
                    # must move only through transition_claim evidence gates.
                    if record.get("status") == "FORM_READY" and claim.get("status") in {
                        "MATCH_FOUND",
                        "FORM_READY",
                        "NEEDS_DOCS",
                    }:
                        claim["status"] = "FORM_READY"
                        claim["progress_pct"] = STATUS_PROGRESS.get("FORM_READY", 0)
                    claim["updated_at"] = now_iso()
                    if claim.get("status") in {"MATCH_FOUND", "FORM_READY"}:
                        claim["next_action"] = (
                            "Resolve conflicts before approval"
                            if record.get("validation_errors")
                            else "Approve and submit form"
                        )
            self._write(data)
        return record

    def get_form(self, claim_id: str) -> dict[str, Any] | None:
        for form in self._read()["forms"]:
            if form.get("claim_id") == claim_id:
                return form
        return None

    def append_evidence(self, evidence: dict[str, Any]) -> dict[str, Any]:
        record = {
            **evidence,
            "id": evidence.get("id") or new_id("evd"),
            "created_at": evidence.get("created_at") or now_iso(),
        }
        with self._lock:
            data = self._read()
            data["evidence"].append(record)
            self._write(data)
        return record

    def evidence(self, claim_id: str | None = None) -> list[dict[str, Any]]:
        values = self._read()["evidence"]
        return [item for item in values if not claim_id or item.get("claim_id") == claim_id]

    def append_memory(self, entry: dict[str, Any]) -> dict[str, Any]:
        record = {**entry, "id": entry.get("id") or new_id("mem"), "created_at": entry.get("created_at") or now_iso()}
        with self._lock:
            data = self._read()
            data["memory_trail"].append(record)
            self._write(data)
        return record

    def memory(self, claim_id: str | None = None) -> list[dict[str, Any]]:
        values = self._read()["memory_trail"]
        return [item for item in values if not claim_id or item.get("claim_id") == claim_id]

    def transition_claim(
        self,
        *,
        claim_id: str,
        to_status: str,
        actor: str,
        evidence_kind: str | None = None,
        source: str = "local_demo",
        reference: str | None = None,
        note: str | None = None,
        payload: dict[str, Any] | None = None,
        claim_updates: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        claim = self.get_claim(claim_id)
        if not claim:
            raise KeyError(f"Unknown claim: {claim_id}")
        from_status = claim["status"]
        required = EVIDENCE_FOR_STATUS.get(to_status)
        kind = evidence_kind or required
        result = can_transition(from_status, to_status, kind)
        if not result.ok:
            raise ValueError(result.error)

        evidence_record = None
        if kind:
            evidence_record = self.append_evidence(
                {
                    "claim_id": claim_id,
                    "kind": kind,
                    "source": source,
                    "reference": reference,
                    "payload": payload or {},
                }
            )

        event = self.append_event(
            {
                "claim_id": claim_id,
                "from_status": from_status,
                "to_status": to_status,
                "actor": actor,
                "evidence_kind": kind,
                "evidence_id": evidence_record["id"] if evidence_record else None,
                "source": source,
                "reference": reference,
                "note": note,
            }
        )

        updates = {
            "status": to_status,
            "last_checked_at": now_iso(),
            **(claim_updates or {}),
        }
        if to_status == "SUBMITTED":
            updates["submitted_at"] = now_iso()
            updates["next_action"] = "Wait for agency receipt"
        elif to_status == "CLAIM_RECEIVED":
            updates["confirmation_id"] = reference or claim.get("confirmation_id")
            updates["next_action"] = "Agency is reviewing the claim"
        elif to_status == "PROCESSING":
            updates["next_action"] = "Check back for agency decision"
        elif to_status == "NEEDS_DOCS":
            updates["next_action"] = "Upload requested documents and resubmit"
        elif to_status == "REJECTED":
            updates["next_action"] = "Review rejection reason"
        elif to_status == "APPROVED":
            updates["approved_at"] = now_iso()
            updates["next_action"] = "Wait for payment issued evidence"
        elif to_status == "PAYMENT_ISSUED":
            updates["payment_issued_at"] = now_iso()
            updates["next_action"] = "Confirm demo bank deposit"
        elif to_status == "PAYMENT_CONFIRMED":
            updates["payment_confirmed_at"] = now_iso()
            updates["next_action"] = "Money flow complete (synthetic)"
        elif to_status == "STOPPED_BY_USER":
            updates["next_action"] = "Stopped by user"

        updated = self.update_claim(claim_id, updates)
        self.append_memory(
            {
                "claim_id": claim_id,
                "kind": "status_transition",
                "summary": f"{from_status} → {to_status}",
                "reason": note or f"Transition allowed with evidence_kind={kind}",
                "evidence_kind": kind,
                "actor": actor,
                "source": source,
            }
        )
        return {"claim": updated, "event": event, "evidence": evidence_record}

    def tracker(self) -> dict[str, Any]:
        data = self._read()
        claims = data["claims"]
        possible = sum(c.get("amount_cents") or 0 for c in claims if c.get("status") not in {"REJECTED", "STOPPED_BY_USER"})
        confirmed = sum(
            c.get("amount_cents") or 0 for c in claims if c.get("status") == "PAYMENT_CONFIRMED"
        )
        needs_review = sum(1 for c in claims if c.get("status") in {"FORM_READY", "NEEDS_DOCS", "MATCH_FOUND"})
        processing = sum(
            1
            for c in claims
            if c.get("status") in {"SUBMITTED", "CLAIM_RECEIVED", "PROCESSING", "APPROVED", "PAYMENT_ISSUED"}
        )
        return {
            "persistence": "json",
            "surreal_schema": "schemas/surreal/schema.surql",
            "surreal_live": False,
            "summary": {
                "possible_funds_cents": possible,
                "confirmed_demo_cents": confirmed,
                "claims_total": len(claims),
                "needs_review": needs_review,
                "processing": processing,
                "confirmed": sum(1 for c in claims if c.get("status") == "PAYMENT_CONFIRMED"),
                "rejected": sum(1 for c in claims if c.get("status") == "REJECTED"),
            },
            "claims": sorted(claims, key=lambda c: c.get("updated_at") or "", reverse=True),
            "events": sorted(data["events"], key=lambda e: e.get("created_at") or "", reverse=True)[:50],
            "evidence": sorted(data["evidence"], key=lambda e: e.get("created_at") or "", reverse=True)[:50],
            "memory_trail": sorted(data["memory_trail"], key=lambda e: e.get("created_at") or "", reverse=True)[:50],
            "profiles": data["profiles"][-5:],
        }

    def reset_demo(self, seed: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            payload = self._empty()
            for key in ("profiles", "claims", "forms", "events", "evidence", "memory_trail", "meta"):
                if key in seed:
                    payload[key] = seed[key]
            payload["meta"] = {
                **payload.get("meta", {}),
                **(seed.get("meta") or {}),
                "seeded_at": now_iso(),
            }
            self._write(payload)
            return payload


def repository() -> EventRepository:
    """Select JSON locally; a future SurrealRepository can be injected here."""
    return JsonEventRepository()
