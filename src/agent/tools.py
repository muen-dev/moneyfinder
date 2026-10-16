"""Agent tool boundary implementations (deterministic side)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.forms.provenance import (
    form_hash,
    prepare_business_claim_fields,
    readback_diff,
    validate_fields,
)
from src.pipeline.status import can_transition
from src.providers.mock_agency import MockAgencyStatusProvider
from src.providers.mock_bank import MockBankTransactionProvider
from src.search.adapter import MockNYUnclaimedAdapter
from src.search.variants import generate_name_variants


class AgentToolbox:
    def __init__(self) -> None:
        self.search = MockNYUnclaimedAdapter()
        self.agency = MockAgencyStatusProvider()
        self.bank = MockBankTransactionProvider()
        self._claims: dict[str, dict[str, Any]] = {}

    def build_search_profile(self, raw: dict) -> dict:
        if not raw.get("search_consent"):
            raise ValueError("search_consent required")
        if raw.get("entity_type") != "business":
            raise ValueError("Only B2B entity_type=business supported in v1")
        return raw

    def generate_name_variants(self, profile: dict) -> list[str]:
        return generate_name_variants(profile["legal_name"], profile.get("dbas"))

    def search_unclaimed(self, profile: dict) -> list[dict]:
        hits = self.search.search(profile)
        return [
            {
                "found_name": h.found_name,
                "property_type": h.property_type,
                "city": h.city,
                "zip": h.zip,
                "amount_cents": h.amount_cents,
                "source": h.source,
                "confidence": h.confidence,
                "reasons": h.reasons,
                "status": "MATCH_FOUND",
            }
            for h in hits
        ]

    def prepare_claim_form(self, profile: dict, hit: dict) -> dict:
        fields = prepare_business_claim_fields(profile, hit)
        return {
            "fields": [f.__dict__ for f in fields],
            "status": "FORM_READY",
            "validation_errors": validate_fields(fields),
        }

    def validate_form(self, fields: list[dict]) -> dict:
        from src.forms.provenance import FormField

        objs = [FormField(**f) for f in fields]
        errors = validate_fields(objs)
        return {"ok": not errors, "errors": errors, "form_hash": form_hash(objs) if not errors else None}

    def request_user_approval(self, form_hash_value: str, approved: bool) -> dict:
        if not approved:
            return {"status": "FORM_READY", "approved": False}
        return {
            "status": "USER_APPROVED",
            "approved": True,
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "form_hash": form_hash_value,
        }

    def daytona_fill_and_submit(
        self,
        *,
        approved_fields: list[dict],
        browser_readback: dict[str, str],
        claim_id: str,
    ) -> dict:
        from src.forms.provenance import FormField

        objs = [FormField(**f) for f in approved_fields]
        if any(f.requires_confirmation for f in objs):
            raise PermissionError("Cannot submit with unresolved confirmation fields")
        diffs = readback_diff(objs, browser_readback)
        if diffs:
            return {"ok": False, "status": "USER_APPROVED", "mismatches": diffs}
        confirmation_id = f"NY-DEMO-{claim_id[-5:].upper()}"
        evidence = {
            "kind": "submission",
            "source": "daytona_mock_portal",
            "reference": confirmation_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.agency.seed(confirmation_id, "CLAIM_RECEIVED")
        self._claims[claim_id] = {
            "status": "CLAIM_RECEIVED",
            "confirmation_id": confirmation_id,
            "amount_cents": None,
        }
        return {
            "ok": True,
            "status": "CLAIM_RECEIVED",
            "confirmation_id": confirmation_id,
            "evidence": evidence,
        }

    def poll_agency_status(self, confirmation_id: str, advance: bool = False) -> dict:
        status = self.agency.advance(confirmation_id) if advance else self.agency.get_status(confirmation_id)
        return {
            "status": status.status,
            "reference": status.reference,
            "checked_at": status.checked_at.isoformat(),
            "raw": status.raw,
        }

    def match_bank_transaction(
        self,
        account_id: str,
        *,
        amount_cents: int,
        confirmation_id: str,
        emit_demo_deposit: bool = False,
    ) -> dict:
        if emit_demo_deposit:
            self.bank.emit_deposit(account_id, amount_cents=amount_cents, reference=confirmation_id)
        match = self.bank.match_payment(
            account_id,
            amount_cents=amount_cents,
            issued_at=datetime.now(timezone.utc),
            reference=confirmation_id,
        )
        if not match:
            return {"matched": False}
        if match.confidence == "LOW":
            return {"matched": False, "needs_user_review": True, "candidate": match.__dict__}
        return {
            "matched": True,
            "confidence": match.confidence,
            "reasons": match.reasons,
            "transaction": {
                "amount_cents": match.transaction.amount_cents,
                "posted_at": match.transaction.posted_at.isoformat(),
                "description": match.transaction.description,
                "reference": match.transaction.reference,
                "synthetic": match.transaction.synthetic,
            },
            "evidence_kind": "bank_deposit",
        }

    def record_evidence_event(
        self,
        *,
        from_status: str,
        to_status: str,
        evidence_kind: str | None,
        actor: str,
    ) -> dict:
        result = can_transition(from_status, to_status, evidence_kind)
        if not result.ok:
            return {"ok": False, "error": result.error}
        return {
            "ok": True,
            "event": {
                "from_status": from_status,
                "to_status": to_status,
                "actor": actor,
                "evidence_kind": evidence_kind,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        }
