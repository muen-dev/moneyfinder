"""Business-scoped Wallet, form review, claim tracker, and fill-job routes."""

from __future__ import annotations

import os

from flask import abort, flash, redirect, render_template, request, url_for

from ..gmail import auth
from ..wallet.contract import OPPORTUNITY_TAX_CREDIT, OPPORTUNITY_UNCLAIMED
from ..wallet.service import WalletService


def register(app) -> None:
    def _conn(business_id: str) -> auth.Connection:
        try:
            return auth.get(business_id)
        except (ValueError, auth.NotConnectedError):
            abort(404)

    def _wallet(business_id: str) -> WalletService:
        _conn(business_id)
        return WalletService(business_id)

    @app.get("/businesses/<business_id>/wallet")
    def wallet(business_id: str):
        conn = _conn(business_id)
        service = WalletService(business_id)
        dossier = service.load_dossier()
        tracker = service.tracker()
        opportunities = tracker.get("opportunities") or []
        return render_template(
            "wallet.html",
            conn=conn,
            dossier=dossier,
            opportunities=opportunities,
            unclaimed=[o for o in opportunities if o.get("opportunity_type") == OPPORTUNITY_UNCLAIMED],
            credits=[o for o in opportunities if o.get("opportunity_type") == OPPORTUNITY_TAX_CREDIT],
            claims=service.store.claims(),
            tracker=tracker,
            source_mode="imported" if os.environ.get("NY_UNCLAIMED_DATA_FILE", "").strip() else "demo_only",
        )

    @app.post("/businesses/<business_id>/wallet/search")
    def wallet_search(business_id: str):
        service = _wallet(business_id)
        consent = request.form.get("consent") == "1"
        try:
            result = service.find_opportunities(consent=consent)
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("wallet", business_id=business_id))
        flash(
            f"Found {result['unclaimed_count']} unclaimed-property matches and "
            f"{result['credit_count']} tax-credit leads ({result['source_mode']}).",
            "ok",
        )
        return redirect(url_for("wallet", business_id=business_id))

    @app.post("/businesses/<business_id>/wallet/opportunities/<opportunity_id>/open")
    def wallet_open_opportunity(business_id: str, opportunity_id: str):
        service = _wallet(business_id)
        opp = service.store.get_opportunity(opportunity_id)
        if not opp:
            abort(404)
        try:
            if opp.get("opportunity_type") == OPPORTUNITY_TAX_CREDIT:
                result = service.select_tax_credit(opportunity_id)
            else:
                result = service.select_unclaimed(opportunity_id, consent=True)
        except (KeyError, ValueError) as e:
            flash(str(e), "error")
            return redirect(url_for("wallet", business_id=business_id))
        return redirect(url_for("wallet_form", business_id=business_id, claim_id=result["claim"]["id"]))

    @app.get("/businesses/<business_id>/forms/<claim_id>")
    def wallet_form(business_id: str, claim_id: str):
        conn = _conn(business_id)
        service = WalletService(business_id)
        try:
            bundle = service.claim_bundle(claim_id)
        except KeyError:
            abort(404)
        form = bundle.get("form") or {}
        fields = form.get("fields") or []
        return render_template(
            "wallet_form.html",
            conn=conn,
            claim=bundle["claim"],
            form=form,
            fields=fields,
            errors=form.get("validation_errors") or [],
            fill_jobs=bundle.get("fill_jobs") or [],
            events=bundle.get("events") or [],
            evidence=bundle.get("evidence") or [],
        )

    @app.post("/businesses/<business_id>/forms/<claim_id>/save")
    def wallet_form_save(business_id: str, claim_id: str):
        service = _wallet(business_id)
        try:
            bundle = service.claim_bundle(claim_id)
        except KeyError:
            abort(404)
        form = bundle.get("form") or {}
        updated = []
        for field in form.get("fields") or []:
            name = field["field"]
            value = request.form.get(f"field_{name}", field.get("value") or "")
            confirm = request.form.get(f"confirm_{name}") == "1"
            row = dict(field)
            if value != field.get("value"):
                row["value"] = value
                row["edited_by_user"] = True
                row["source"] = "edited_by_user"
            if confirm:
                row["requires_confirmation"] = False
                row["conflicting_value"] = None
                row["source_of_conflict"] = None
                row["edited_by_user"] = True
                row["source"] = row.get("source") or "edited_by_user"
            updated.append(row)
        result = service.save_form_fields(claim_id, updated)
        if result["ok"]:
            flash("Form saved. Ready for approval.", "ok")
        else:
            flash("Saved with remaining issues: " + "; ".join(result["errors"][:4]), "error")
        return redirect(url_for("wallet_form", business_id=business_id, claim_id=claim_id))

    @app.post("/businesses/<business_id>/forms/<claim_id>/approve")
    def wallet_form_approve(business_id: str, claim_id: str):
        service = _wallet(business_id)
        if request.form.get("approved") != "1":
            flash("Authorization checkbox is required.", "error")
            return redirect(url_for("wallet_form", business_id=business_id, claim_id=claim_id))
        try:
            service.approve_form(claim_id, approved=True)
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("wallet_form", business_id=business_id, claim_id=claim_id))
        flash("Form snapshot approved. You can run the browser fill (it will not submit).", "ok")
        return redirect(url_for("wallet_form", business_id=business_id, claim_id=claim_id))

    @app.post("/businesses/<business_id>/forms/<claim_id>/fill")
    def wallet_form_fill(business_id: str, claim_id: str):
        service = _wallet(business_id)
        try:
            result = service.run_fill(claim_id)
        except (KeyError, PermissionError, ValueError) as e:
            flash(str(e), "error")
            return redirect(url_for("wallet_form", business_id=business_id, claim_id=claim_id))
        status = result["receipt"].get("status")
        flash(f"Fill finished: {status}. Submitted: false.", "ok")
        return redirect(url_for("wallet_form", business_id=business_id, claim_id=claim_id))

    @app.get("/businesses/<business_id>/claims/<claim_id>")
    def wallet_claim(business_id: str, claim_id: str):
        conn = _conn(business_id)
        service = WalletService(business_id)
        try:
            bundle = service.claim_bundle(claim_id)
        except KeyError:
            abort(404)
        return render_template(
            "wallet_claim.html",
            conn=conn,
            claim=bundle["claim"],
            form=bundle.get("form"),
            events=bundle.get("events") or [],
            evidence=bundle.get("evidence") or [],
            memory=bundle.get("memory_trail") or [],
            fill_jobs=bundle.get("fill_jobs") or [],
        )

    @app.get("/businesses/<business_id>/tracker")
    def wallet_tracker(business_id: str):
        conn = _conn(business_id)
        service = WalletService(business_id)
        return render_template(
            "wallet_tracker.html",
            conn=conn,
            tracker=service.tracker(),
            claims=service.store.claims(),
        )
