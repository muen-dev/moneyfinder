"""Wallet orchestration: search, claim/form lifecycle, approval-gated fill jobs."""

from __future__ import annotations

import os
from typing import Any

from .. import company, dossier as dossiers
from . import _repo, contract, fill_job
from .store import BusinessWalletStore

_repo.ensure_repo_on_path()

from src.agent.tools import AgentToolbox  # noqa: E402
from src.forms.provenance import FormField, form_hash, validate_fields  # noqa: E402
from src.persistence import now_iso  # noqa: E402


class WalletService:
    def __init__(self, business_id: str, *, tools: AgentToolbox | None = None):
        self.business_id = business_id
        self.store = BusinessWalletStore(business_id)
        self.tools = tools or AgentToolbox()

    def load_dossier(self, *, refresh: bool = False) -> dict[str, Any] | None:
        cached = None if refresh else dossiers.cached_for_business(self.business_id)
        if cached:
            return cached
        domain = company.get_domain(self.business_id)
        if domain and not refresh:
            cached = dossiers.cached_for_domain(domain)
            if cached:
                return cached
        try:
            return dossiers.build_for_business(self.business_id, use_llm=False)
        except Exception:
            if domain:
                try:
                    return dossiers.build_for_domain(domain, business_id=self.business_id, use_llm=False)
                except Exception:
                    return None
            return None

    def search_profile(self, dossier: dict[str, Any] | None = None, *, consent: bool = True) -> dict[str, Any]:
        dossier = dossier or self.load_dossier()
        if not dossier:
            raise ValueError("No dossier yet. Add a company domain and finish research first.")
        return contract.dossier_to_search_profile(dossier, business_id=self.business_id, consent=consent)

    def find_opportunities(self, *, consent: bool = True, refresh_dossier: bool = False) -> dict[str, Any]:
        dossier = self.load_dossier(refresh=refresh_dossier)
        if not dossier:
            raise ValueError("No dossier yet. Add a company domain and finish research first.")
        profile = contract.dossier_to_search_profile(dossier, business_id=self.business_id, consent=consent)
        if not profile["search_consent"]:
            raise ValueError("Consent is required before searching for opportunities.")

        source_mode = "imported" if os.environ.get("NY_UNCLAIMED_DATA_FILE", "").strip() else "demo_only"
        hits = self.tools.search_unclaimed(profile)
        unclaimed = [
            contract.hit_to_opportunity(
                hit, business_id=self.business_id, slug=profile["dossier_slug"], source_mode=source_mode
            )
            for hit in hits
        ]
        credits = [
            contract.credit_to_opportunity(c, business_id=self.business_id, slug=profile["dossier_slug"])
            for c in (dossier.get("credits") or [])
            if c.get("status") != "expired"
        ]
        opportunities = self.store.save_opportunities(unclaimed + credits)
        self.store.repo.append_memory(
            {
                "claim_id": None,
                "kind": "wallet_search",
                "summary": f"Found {len(unclaimed)} unclaimed + {len(credits)} credit opportunities",
                "reason": "User opened Wallet / Find opportunities",
                "actor": "user",
                "source": "wallet",
                "business_id": self.business_id,
            }
        )
        return {
            "business_id": self.business_id,
            "profile": profile,
            "dossier_slug": profile["dossier_slug"],
            "source_mode": source_mode,
            "opportunities": opportunities,
            "unclaimed_count": len(unclaimed),
            "credit_count": len(credits),
        }

    def select_unclaimed(self, opportunity_id: str, *, consent: bool = True) -> dict[str, Any]:
        opp = self.store.get_opportunity(opportunity_id)
        if not opp or opp.get("opportunity_type") != contract.OPPORTUNITY_UNCLAIMED:
            raise KeyError("Unknown unclaimed-property opportunity")
        profile = self.search_profile(consent=consent)
        hit = opp.get("hit") or {
            "found_name": opp.get("title"),
            "property_type": opp.get("property_type"),
            "city": opp.get("city"),
            "zip": opp.get("zip"),
            "amount_cents": opp.get("amount_cents"),
            "confidence": opp.get("confidence"),
            "reasons": opp.get("reasons"),
            "source": opp.get("source"),
            "force_demo_conflict": False,
        }
        # Avoid inventing ZIP conflicts for imported/official data.
        hit.setdefault("force_demo_conflict", bool(opp.get("demo_only")))
        claim = self.store.repo.create_claim(
            {
                "business_name": profile.get("legal_name"),
                "business_id": self.business_id,
                "match_name": hit.get("found_name"),
                "property_type": hit.get("property_type"),
                "city": hit.get("city"),
                "zip": hit.get("zip"),
                "amount_cents": hit.get("amount_cents"),
                "confidence": hit.get("confidence"),
                "status": "MATCH_FOUND",
                "hit": hit,
                "profile": profile,
                "demo_only": bool(opp.get("demo_only")),
                "source": hit.get("source"),
                "next_action": "Prepare claim form",
            }
        )
        self.store.repo.update_claim(
            claim["id"],
            {
                "opportunity_type": contract.OPPORTUNITY_UNCLAIMED,
                "opportunity_id": opp.get("wallet_id") or opportunity_id,
            },
        )
        prepared = self.tools.prepare_claim_form(profile, hit)
        form = self.store.repo.save_form(
            {
                "claim_id": claim["id"],
                "fields": prepared["fields"],
                "status": "FORM_READY",
                "validation_errors": prepared["validation_errors"],
                "agency": "NY Office of Unclaimed Funds",
                "form_hash": None,
                "approved": False,
                "opportunity_type": contract.OPPORTUNITY_UNCLAIMED,
            }
        )
        self.store.repo.update_claim(
            claim["id"],
            {
                "status": "FORM_READY",
                "next_action": (
                    "Resolve conflicts before approval"
                    if prepared["validation_errors"]
                    else "Approve form snapshot"
                ),
            },
        )
        self.store.repo.append_event(
            {
                "claim_id": claim["id"],
                "from_status": "MATCH_FOUND",
                "to_status": "FORM_READY",
                "actor": "agent",
                "source": "wallet.prepare",
                "note": "Form prepared with provenance",
            }
        )
        return {"claim": self.store.get_claim(claim["id"]), "form": form, "opportunity": opp}

    def select_tax_credit(self, opportunity_id: str) -> dict[str, Any]:
        opp = self.store.get_opportunity(opportunity_id)
        if not opp or opp.get("opportunity_type") != contract.OPPORTUNITY_TAX_CREDIT:
            raise KeyError("Unknown tax-credit opportunity")
        profile = self.search_profile(consent=True)
        forms = opp.get("forms") or []
        primary = forms[0] if forms else {}
        claim = self.store.repo.create_claim(
            {
                "business_name": profile.get("legal_name"),
                "business_id": self.business_id,
                "match_name": opp.get("title"),
                "property_type": f"Tax credit · {primary.get('code') or 'form'}",
                "city": (profile.get("addresses") or [{}])[0].get("city"),
                "zip": (profile.get("addresses") or [{}])[0].get("zip"),
                "amount_cents": None,
                "amount_type": "not_disclosed",
                "confidence": opp.get("confidence"),
                "status": "MATCH_FOUND",
                "hit": {"credit": opp, "forms": forms},
                "profile": profile,
                "demo_only": False,
                "source": "legal_catalog",
                "next_action": "Review credit form fields",
            }
        )
        self.store.repo.update_claim(
            claim["id"],
            {
                "opportunity_type": contract.OPPORTUNITY_TAX_CREDIT,
                "opportunity_id": opp.get("wallet_id") or opportunity_id,
            },
        )
        fields = self._credit_form_fields(profile, opp)
        errors = validate_fields([FormField(**f) for f in fields])
        form = self.store.repo.save_form(
            {
                "claim_id": claim["id"],
                "fields": fields,
                "status": "FORM_READY",
                "validation_errors": errors,
                "agency": opp.get("jurisdiction") or "NYS",
                "form_code": primary.get("code"),
                "form_url": primary.get("url") or primary.get("pdf"),
                "form_hash": None,
                "approved": False,
                "opportunity_type": contract.OPPORTUNITY_TAX_CREDIT,
            }
        )
        self.store.repo.update_claim(
            claim["id"],
            {
                "status": "FORM_READY",
                "next_action": "Resolve missing fields before approval" if errors else "Approve form snapshot",
            },
        )
        return {"claim": self.store.get_claim(claim["id"]), "form": form, "opportunity": opp}

    def save_form_fields(self, claim_id: str, fields_raw: list[dict[str, Any]]) -> dict[str, Any]:
        claim = self.store.get_claim(claim_id)
        if not claim:
            raise KeyError("claim_not_found")
        objs = [FormField(**f) for f in fields_raw]
        errors = validate_fields(objs)
        fh = form_hash(objs) if not errors else None
        existing = self.store.repo.get_form(claim_id) or {}
        form = self.store.repo.save_form(
            {
                **existing,
                "claim_id": claim_id,
                "fields": [f.__dict__ for f in objs],
                "status": "FORM_READY",
                "validation_errors": errors,
                "form_hash": fh,
                "approved": False,
            }
        )
        self.store.repo.update_claim(
            claim_id,
            {
                "form_hash": fh,
                "next_action": "Resolve conflicts before approval" if errors else "Approve form snapshot",
            },
        )
        return {"form": form, "ok": not errors, "errors": errors}

    def approve_form(self, claim_id: str, *, approved: bool) -> dict[str, Any]:
        claim = self.store.get_claim(claim_id)
        form = self.store.repo.get_form(claim_id)
        if not claim or not form:
            raise KeyError("form_not_found")
        objs = [FormField(**f) for f in form["fields"]]
        errors = validate_fields(objs)
        if errors:
            raise ValueError("form_not_ready")
        if not approved:
            raise ValueError("authorization_required")
        fh = form_hash(objs)
        result = self.store.repo.transition_claim(
            claim_id=claim_id,
            to_status="USER_APPROVED",
            actor="user",
            evidence_kind=None,
            source="user_approval",
            note="Authorized representative approved immutable form snapshot",
            claim_updates={"form_hash": fh, "next_action": "Run browser fill (no submit)"},
        )
        form = self.store.repo.save_form({**form, "approved": True, "form_hash": fh, "status": "USER_APPROVED"})
        snapshot = fill_job.plan_from_approved_form(form)
        return {"form": form, "snapshot": snapshot, **result}

    def run_fill(self, claim_id: str) -> dict[str, Any]:
        claim = self.store.get_claim(claim_id)
        form = self.store.repo.get_form(claim_id)
        if not claim or not form:
            raise KeyError("form_not_found")
        if not form.get("approved") or claim.get("status") != "USER_APPROVED":
            raise PermissionError("Form must be approved before browser fill")
        snapshot = fill_job.plan_from_approved_form(form)
        if not snapshot.get("approved"):
            raise PermissionError("Approved snapshot required")

        # Default: simulated fill (safe in CI). Live Anchor is opt-in and still never submits.
        if fill_job.live_anchor_enabled():
            receipt = self._run_live_anchor(claim, form, snapshot)
        else:
            mode = "tax_pdf" if claim.get("opportunity_type") == contract.OPPORTUNITY_TAX_CREDIT else "mock_portal"
            receipt = fill_job.simulate_fill(snapshot, mode=mode)

        out_dir = self.store.root / "fill-receipts"
        path = fill_job.write_receipt(out_dir / f"{claim_id}-{receipt['created_at'].replace(':', '')}.json", receipt)
        job = self.store.save_fill_job(
            {
                "claim_id": claim_id,
                "business_id": self.business_id,
                "status": receipt.get("status"),
                "submitted": False,
                "receipt_path": str(path),
                "receipt": receipt,
                "snapshot_hash": snapshot.get("form_hash"),
            }
        )
        self.store.repo.append_evidence(
            {
                "claim_id": claim_id,
                "kind": "browser_readback",
                "source": "wallet.fill_job",
                "reference": job["id"],
                "payload": {
                    "status": receipt.get("status"),
                    "submitted": False,
                    "mismatches": receipt.get("mismatches") or [],
                },
            }
        )
        self.store.repo.append_memory(
            {
                "claim_id": claim_id,
                "kind": "browser_fill",
                "summary": f"Fill job {receipt.get('status')} (submitted=false)",
                "reason": "Approval-gated Anchor/simulate runner",
                "actor": "agent",
                "source": "wallet.fill_job",
            }
        )
        self.store.repo.update_claim(
            claim_id,
            {
                "next_action": (
                    "Fix browser mismatches"
                    if receipt.get("mismatches")
                    else "Review filled form; submit only after final OK"
                ),
                "fill_job_id": job["id"],
                "fill_status": receipt.get("status"),
            },
        )
        return {"job": job, "receipt": receipt, "snapshot": snapshot, "claim": self.store.get_claim(claim_id)}

    def tracker(self) -> dict[str, Any]:
        return self.store.tracker()

    def claim_bundle(self, claim_id: str) -> dict[str, Any]:
        bundle = self.store.claim_bundle(claim_id)
        if not bundle:
            raise KeyError("claim_not_found")
        return bundle

    def _credit_form_fields(self, profile: dict[str, Any], opp: dict[str, Any]) -> list[dict[str, Any]]:
        addr = (profile.get("addresses") or [{}])[0]
        rep = profile.get("authorized_representative") or {}
        dossier = self.load_dossier() or {}
        business = dossier.get("business") or {}
        rows = [
            ("legal_name", profile.get("legal_name") or business.get("legal_name") or "", "dossier", 0.95),
            ("authorized_representative", rep.get("name") or business.get("officer_name") or "", "user", 0.9),
            ("role", rep.get("role") or business.get("officer_title") or "", "user", 0.9),
            ("city", addr.get("city") or "", "dossier", 0.85),
            ("zip", addr.get("zip") or "", "dossier", 0.85),
            ("program", opp.get("title") or "", "legal_catalog", 0.99),
            ("form_code", ((opp.get("forms") or [{}])[0].get("code") or ""), "legal_catalog", 0.99),
            ("pay_to", profile.get("legal_name") or "", "dossier", 0.9),
        ]
        fields = []
        for name, value, source, conf in rows:
            requires = not bool(str(value).strip()) and name in {
                "legal_name",
                "authorized_representative",
                "city",
                "zip",
            }
            fields.append(
                {
                    "field": name,
                    "value": str(value or ""),
                    "source": source,
                    "confidence": conf,
                    "requires_confirmation": requires,
                    "conflicting_value": None,
                    "source_of_conflict": None,
                    "edited_by_user": False,
                }
            )
        return fields

    def _run_live_anchor(self, claim: dict[str, Any], form: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
        """Optional live path: still never submits. Falls back to simulate on failure."""
        try:
            # Import only when opted in; keep Flask boot light.
            from form_filling import fill as fill_mod  # type: ignore
        except Exception:
            return fill_job.simulate_fill(snapshot, mode="live_anchor_unavailable")
        # Live runner is CLI-oriented; for the unified app we still emit a non-submit receipt.
        _ = (claim, form, fill_mod)
        receipt = fill_job.simulate_fill(snapshot, mode="live_anchor_planned")
        receipt["note"] = (
            "WALLET_LIVE_ANCHOR=1 is set, but the unified Wallet uses the approved snapshot receipt path. "
            "Use `make fill --claim-id ...` for a watched Anchor session; it never auto-submits."
        )
        receipt["live_anchor"] = True
        return receipt
