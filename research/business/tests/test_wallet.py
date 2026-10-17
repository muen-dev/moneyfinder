"""Unified Wallet: dossier → opportunities → form review → approve → fill (no submit)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from business_research import config, ids
from business_research.wallet.contract import (
    OPPORTUNITY_TAX_CREDIT,
    OPPORTUNITY_UNCLAIMED,
    dossier_to_search_profile,
    hit_to_opportunity,
)
from business_research.wallet.fill_job import plan_from_approved_form, simulate_fill
from business_research.wallet.service import WalletService
from business_research.web.app import create_app

BASE = "http://localhost:8000"
EMAIL = "owner@joespizza.com"
REPO = Path(__file__).resolve().parents[3]


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "TOKEN_DIR", tmp_path / "tokens")
    monkeypatch.setattr(config, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(config, "CLIENT_SECRETS_FILE", tmp_path / "credentials.json")
    monkeypatch.delenv("NY_UNCLAIMED_DATA_FILE", raising=False)
    monkeypatch.delenv("WALLET_LIVE_ANCHOR", raising=False)
    return create_app(8000).test_client()


def connect_fake_business() -> str:
    business_id = ids.from_email(EMAIL)
    config.TOKEN_DIR.mkdir(parents=True, exist_ok=True)
    (config.TOKEN_DIR / f"{business_id}.json").write_text(
        json.dumps(
            {
                "email": EMAIL,
                "connected_at": "2026-10-16T12:00:00+00:00",
                "credentials": {"client_id": "id", "client_secret": "s", "refresh_token": "rt", "token": "at"},
            }
        )
    )
    return business_id


def set_csrf(client, token="test-csrf"):
    with client.session_transaction(base_url=BASE) as session:
        session["csrf"] = token
    return token


def seed_dossier(business_id: str) -> dict:
    out = config.DATA_DIR / business_id
    out.mkdir(parents=True, exist_ok=True)
    dossier = {
        "schema": "moneyfinder.dossier/v1",
        "slug": "joespizza-com",
        "domain": "joespizza.com",
        "business": {
            "legal_name": "Example NYC Foods LLC",
            "name": "Example NYC Foods",
            "hq_address": "123 Main Street, Brooklyn, NY 11201",
            "officer_name": "Maria Alvarez",
            "officer_title": "Managing Member",
            "entity_type": "Domestic Limited Liability Company",
        },
        "facts": [
            {
                "key": "hq_address",
                "value": "123 Main Street, Brooklyn, NY 11201",
                "source_kind": "registry",
                "source": "nys_dos",
                "confidence": 0.9,
            }
        ],
        "credits": [
            {
                "id": "nys_hire_a_veteran",
                "name": "Hire a Veteran Credit",
                "jurisdiction": "NYS",
                "status": "possible",
                "why": ["Hiring signals"],
                "forms": [{"code": "IT-643", "url": "https://www.tax.ny.gov/example.pdf"}],
            }
        ],
        "missing_info": [],
    }
    (out / "dossier.json").write_text(json.dumps(dossier))
    (out / "business.json").write_text(
        json.dumps({"domain": "joespizza.com", "name": "Example NYC Foods", "updated_at": "2026-10-01T00:00:00+00:00"})
    )
    return dossier


def test_dossier_to_search_profile_carries_business_scope():
    dossier = {
        "slug": "acme-com",
        "domain": "acme.com",
        "business": {
            "legal_name": "Acme LLC",
            "hq_address": "1 Main St, Brooklyn, NY 11201",
            "officer_name": "Pat",
            "officer_title": "Owner",
        },
        "facts": [],
    }
    profile = dossier_to_search_profile(dossier, business_id="owner-acme-com", consent=True)
    assert profile["business_id"] == "owner-acme-com"
    assert profile["legal_name"] == "Acme LLC"
    assert profile["addresses"][0]["city"] == "Brooklyn"
    assert profile["addresses"][0]["zip"] == "11201"
    assert profile["search_consent"] is True


def test_hit_to_opportunity_marks_demo_and_missing_amount():
    demo = hit_to_opportunity(
        {"found_name": "A", "source": "mock_ny_unclaimed", "amount_cents": 100, "confidence": 0.9},
        business_id="b",
        slug="s",
        source_mode="demo_only",
    )
    assert demo["opportunity_type"] == OPPORTUNITY_UNCLAIMED
    assert demo["demo_only"] is True
    official = hit_to_opportunity(
        {"found_name": "B", "source": "provider:ny", "amount_cents": None, "confidence": 0.8},
        business_id="b",
        slug="s",
        source_mode="imported",
    )
    assert official["demo_only"] is False
    assert official["amount_status"] == "not_disclosed"


def test_simulate_fill_never_submits_and_requires_approval():
    snapshot = {
        "approved": True,
        "submit": False,
        "form_hash": "abc",
        "claim_id": "claim_1",
        "fields": [{"field": "legal_name", "value": "Acme LLC", "source": "user"}],
        "needs_user": [],
    }
    receipt = simulate_fill(snapshot)
    assert receipt["submitted"] is False
    assert receipt["status"] == "ready_for_user_submission"
    with pytest.raises(PermissionError):
        simulate_fill({**snapshot, "approved": False})


def test_wallet_end_to_end_service(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path / "data")
    monkeypatch.delenv("NY_UNCLAIMED_DATA_FILE", raising=False)
    business_id = "owner-joespizza-com"
    seed_dossier(business_id)
    service = WalletService(business_id)
    found = service.find_opportunities(consent=True)
    assert found["unclaimed_count"] >= 1
    assert found["credit_count"] >= 1
    unclaimed = next(o for o in found["opportunities"] if o["opportunity_type"] == OPPORTUNITY_UNCLAIMED)
    credit = next(o for o in found["opportunities"] if o["opportunity_type"] == OPPORTUNITY_TAX_CREDIT)

    selected = service.select_unclaimed(unclaimed["wallet_id"], consent=True)
    claim_id = selected["claim"]["id"]
    assert selected["claim"]["business_id"] == business_id
    assert selected["form"]["status"] == "FORM_READY"

    # Clear any demo ZIP conflict so approval can proceed.
    fields = selected["form"]["fields"]
    for field in fields:
        field["requires_confirmation"] = False
        field["conflicting_value"] = None
        field["edited_by_user"] = True
        if not field.get("value"):
            field["value"] = "x"
    service.save_form_fields(claim_id, fields)
    approved = service.approve_form(claim_id, approved=True)
    assert approved["claim"]["status"] == "USER_APPROVED"
    assert approved["snapshot"]["approved"] is True
    assert approved["snapshot"]["submit"] is False

    filled = service.run_fill(claim_id)
    assert filled["receipt"]["submitted"] is False
    assert filled["job"]["submitted"] is False
    bundle = service.claim_bundle(claim_id)
    assert any(e.get("kind") == "browser_readback" for e in bundle["evidence"])

    # Tax credit path creates a separate claim.
    credit_result = service.select_tax_credit(credit["wallet_id"])
    assert credit_result["claim"]["opportunity_type"] == OPPORTUNITY_TAX_CREDIT
    assert credit_result["form"]["form_code"] == "IT-643"

    tracker = service.tracker()
    assert tracker["business_id"] == business_id
    assert tracker["summary"]["claims_total"] == 2


def test_wallet_routes_require_connected_business_and_csrf(client):
    business_id = connect_fake_business()
    seed_dossier(business_id)
    # Unknown business
    assert client.get("/businesses/not-a-real-biz/wallet", base_url=BASE).status_code == 404
    # Connected wallet page
    page = client.get(f"/businesses/{business_id}/wallet", base_url=BASE)
    assert page.status_code == 200
    assert b"Opportunity Wallet" in page.data
    assert b"Find opportunities" in page.data
    # CSRF required on POST
    bad = client.post(f"/businesses/{business_id}/wallet/search", data={"consent": "1"}, base_url=BASE)
    assert bad.status_code == 403
    csrf = set_csrf(client)
    ok = client.post(
        f"/businesses/{business_id}/wallet/search",
        data={"csrf": csrf, "consent": "1"},
        base_url=BASE,
        follow_redirects=True,
    )
    assert ok.status_code == 200
    assert b"unclaimed-property" in ok.data or b"Unclaimed property" in ok.data


def test_cross_business_claim_access(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path / "data")
    a, b = "owner-a-com", "owner-b-com"
    seed_dossier(a)
    seed_dossier(b)
    sa, sb = WalletService(a), WalletService(b)
    found = sa.find_opportunities(consent=True)
    opp = next(o for o in found["opportunities"] if o["opportunity_type"] == OPPORTUNITY_UNCLAIMED)
    claim_id = sa.select_unclaimed(opp["wallet_id"])["claim"]["id"]
    assert sa.store.get_claim(claim_id) is not None
    assert sb.store.get_claim(claim_id) is None
    with pytest.raises(KeyError):
        sb.claim_bundle(claim_id)


def test_plan_from_approved_form_skips_confirmation_fields():
    form = {
        "claim_id": "c1",
        "approved": True,
        "form_hash": "h",
        "fields": [
            {"field": "legal_name", "value": "Acme", "source": "user", "confidence": 1.0,
             "requires_confirmation": False, "conflicting_value": None, "source_of_conflict": None,
             "edited_by_user": False},
            {"field": "zip", "value": "11201", "source": "user", "confidence": 0.7,
             "requires_confirmation": True, "conflicting_value": "11202", "source_of_conflict": "state",
             "edited_by_user": False},
        ],
    }
    snap = plan_from_approved_form(form)
    assert [f["field"] for f in snap["fields"]] == ["legal_name"]
    assert snap["needs_user"][0]["field"] == "zip"
    assert snap["submit"] is False
