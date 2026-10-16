"""Local API for the MoneyFinder end-to-end journey.

Run from the repository root:
    python3 -m src.server

The UI talks to this boundary instead of owning search and event state.
/api/research returns stored research/company/data/<domain>/ output (profile.json,
plus dossier.json under `dossier`) when it exists. Otherwise it returns a demo stub,
unless COMPANY_RESEARCH_LIVE=1, which runs `uv run --project research/company
company-research run <domain>` (needs `make setup` and provider keys; costs API credits).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .agent.orchestrator import MoneyFinderAgent
from .forms.provenance import FormField, form_hash, validate_fields
from .persistence import new_id, now_iso, repository
from .pipeline.status import can_transition
from .profile_mapper import company_profile_to_search_profile

ROOT = Path(__file__).resolve().parents[1]
UI_ROOT = ROOT / "ui"
UI_ENTRY = UI_ROOT / "domain.html"
COMPANY_PROJECT = ROOT / "research" / "company"
# Same env var research/company's config uses, so the server reads where the CLI writes.
COMPANY_DATA_DIR = Path(os.environ.get("COMPANY_DATA_DIR", COMPANY_PROJECT / "data"))
COMPANY_RESEARCH_TIMEOUT_S = int(os.environ.get("COMPANY_RESEARCH_TIMEOUT", "240"))
SEED_PATH = ROOT / "fixtures" / "demo-seed.json"
EVENTS = repository()
AGENT = MoneyFinderAgent()


def _demo_research(domain: str) -> dict:
    name = domain.split(".", 1)[0].replace("-", " ").replace("_", " ").title()
    return {
        "schema_version": 1,
        "domain": domain,
        "generated_at": "demo",
        "best": {
            "legal_name": name,
            "hq_address": "",
            "city": "",
            "state": "NY",
            "zip": "",
            "entity_type": "Needs confirmation",
        },
        "fields": {},
        "collectors": {
            "website": {"status": "demo", "source": domain},
            "nys_dos": {"status": "not_run"},
            "nyc_open_data": {"status": "not_run"},
        },
        "demo_only": True,
    }


_DOMAIN_RE = re.compile(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+")
# "street..., City, ST 12345[-6789]" as written by the company-research collectors.
_ADDRESS_RE = re.compile(
    r"^(?P<street>.+?),\s*(?P<city>[^,]+?),\s*(?P<state>[A-Z]{2})\.?\s+(?P<zip>\d{5})(?:-\d{4})?"
    r"(?:\s*,\s*(?:USA?|United States))?\s*$"
)


def _normalize_domain(raw: str) -> str:
    text = (raw or "").strip().lower()
    text = re.sub(r"^[a-z][a-z0-9+.-]*://", "", text).split("/", 1)[0].split("?", 1)[0].rstrip(".")
    if text.startswith("www."):
        text = text[4:]
    if not _DOMAIN_RE.fullmatch(text):
        raise ValueError("A public business domain is required")
    return text


def _read_json(path: Path) -> dict | None:
    try:
        value = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _adapt_stored_profile(domain: str, profile: dict | None, dossier: dict | None) -> dict:
    """Shape stored research/company output the way company_profile_to_search_profile reads it.

    The collectors store hq_address as one line ("417 Sackett Street, Brooklyn, NY 11231") and a
    single `dba`; the mapper and UI want street / city / state / zip and a `dbas` list.
    """
    profile = dict(profile or {"schema_version": 1, "domain": domain, "fields": {}, "collectors": {}})
    profile.setdefault("domain", domain)
    profile.setdefault("generated_at", (dossier or {}).get("generated_at"))
    best = dict(profile.get("best") or {})
    business = (dossier or {}).get("business") or {}
    for key in ("legal_name", "dba", "hq_address", "entity_type"):
        if not best.get(key) and business.get(key):
            best[key] = business[key]
    full_address = str(best.get("hq_address") or "")
    match = _ADDRESS_RE.match(full_address.strip())
    if match:
        best["hq_address_full"] = full_address
        best["hq_address"] = match["street"].strip()
        for key in ("city", "state", "zip"):
            if not best.get(key):
                best[key] = match[key].strip()
    if not best.get("dbas"):
        best["dbas"] = [best["dba"]] if best.get("dba") else []
    if not best.get("authorized_representative") and business.get("officer_name"):
        best["authorized_representative"] = {
            "name": business["officer_name"],
            "role": business.get("officer_title") or "",
        }
    profile["best"] = best
    profile.setdefault("fields", {})
    if dossier is not None:
        profile["dossier"] = dossier
    return profile


def _stored_research(domain: str) -> dict | None:
    folder = COMPANY_DATA_DIR / domain
    profile = _read_json(folder / "profile.json")
    dossier = _read_json(folder / "dossier.json")
    if profile is None and dossier is None:
        return None
    result = _adapt_stored_profile(domain, profile, dossier)
    result["research_mode"] = "stored"
    return result


def _live_research_command(domain: str, out_dir: Path) -> list[str]:
    uv = shutil.which("uv")
    if not uv:
        raise FileNotFoundError("uv is not installed; it is needed to run company research live")
    return [uv, "run", "--project", str(COMPANY_PROJECT), "company-research", "run", domain, "--out", str(out_dir)]


def _run_live_research(domain: str) -> None:
    command = _live_research_command(domain, COMPANY_DATA_DIR / domain)
    try:
        done = subprocess.run(
            command, cwd=ROOT, capture_output=True, text=True, timeout=COMPANY_RESEARCH_TIMEOUT_S, check=False
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Company research timed out after {COMPANY_RESEARCH_TIMEOUT_S}s") from exc
    if done.returncode != 0:
        detail = (done.stderr or done.stdout or "").strip().splitlines()[-1:] or ["no output"]
        raise RuntimeError(f"Company research failed: {detail[0][:300]}")


def research_domain(domain: str) -> dict:
    """Stored research/company output if present, else live research (COMPANY_RESEARCH_LIVE=1), else a demo stub."""
    domain = _normalize_domain(domain)
    stored = _stored_research(domain)
    if stored is not None:
        return stored
    if os.environ.get("COMPANY_RESEARCH_LIVE") != "1":
        return _demo_research(domain)
    _run_live_research(domain)
    stored = _stored_research(domain)
    if stored is None:
        raise RuntimeError(f"Company research finished but wrote no profile for {domain}")
    stored["research_mode"] = "live"
    return stored


def _load_seed() -> dict:
    if SEED_PATH.exists():
        return json.loads(SEED_PATH.read_text())
    return {
        "profiles": [],
        "claims": [],
        "forms": [],
        "events": [],
        "evidence": [],
        "memory_trail": [],
        "meta": {"demo_business": "Example NYC Foods LLC"},
    }


def _claim_bundle(claim_id: str) -> dict:
    claim = EVENTS.get_claim(claim_id)
    if not claim:
        raise KeyError(f"Unknown claim: {claim_id}")
    return {
        "claim": claim,
        "form": EVENTS.get_form(claim_id),
        "events": EVENTS.events(claim_id),
        "evidence": EVENTS.evidence(claim_id),
        "memory_trail": EVENTS.memory(claim_id),
        "persistence": "json",
        "surreal_live": False,
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "MoneyFinderLocal/1.0"

    def log_message(self, *_args) -> None:
        return

    def _json(self, status: int, value: dict | list) -> None:
        payload = json.dumps(value, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")

    def _static(self, path: Path, content_type: str) -> None:
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/api/health":
            return self._json(
                200,
                {
                    "ok": True,
                    "money_source": "imported" if os.getenv("NY_UNCLAIMED_DATA_FILE") else "demo",
                    "persistence": "json",
                    "surreal_live": False,
                },
            )
        if path == "/api/events":
            claim_id = (query.get("claim_id") or [None])[0]
            return self._json(200, EVENTS.events(claim_id))
        if path == "/api/tracker":
            return self._json(200, EVENTS.tracker())
        if path == "/api/claims":
            return self._json(200, {"claims": EVENTS.claims()})
        if path.startswith("/api/claims/"):
            claim_id = path.split("/api/claims/", 1)[1].strip("/")
            try:
                return self._json(200, _claim_bundle(claim_id))
            except KeyError as exc:
                return self._json(404, {"error": str(exc)})
        if path in ("/", "/index.html", "/domain.html"):
            return self._static(UI_ENTRY, "text/html; charset=utf-8")
        if path == "/ui/legacy.html" and (UI_ROOT / "index.html").exists():
            return self._static(UI_ROOT / "index.html", "text/html; charset=utf-8")
        return self._json(404, {"error": "not_found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            body = self._body()

            if path == "/api/research":
                profile = research_domain(str(body.get("domain", "")).strip())
                return self._json(200, profile)

            if path == "/api/profile/review":
                profile = body.get("profile") or {}
                mapped = company_profile_to_search_profile(profile, consent=bool(body.get("consent")))
                if not mapped["search_consent"]:
                    return self._json(400, {"error": "consent_required"})
                # Preserve explicit manual fields when provided.
                if body.get("manual"):
                    mapped.update({k: v for k, v in body["manual"].items() if v is not None})
                    mapped["search_consent"] = True
                saved = EVENTS.save_profile(mapped)
                EVENTS.append_memory(
                    {
                        "claim_id": None,
                        "kind": "profile_saved",
                        "summary": f"Remembered business profile for {saved.get('legal_name')}",
                        "reason": "User confirmed profile facts before search",
                        "facts": {
                            "legal_name": saved.get("legal_name"),
                            "dbas": saved.get("dbas"),
                            "addresses": saved.get("addresses"),
                            "representative": saved.get("authorized_representative"),
                        },
                        "actor": "user",
                        "source": "profile_review",
                    }
                )
                return self._json(200, {"profile": saved})

            if path == "/api/search":
                profile = body.get("profile") or {}
                hits = AGENT.build_and_search(profile)
                return self._json(
                    200,
                    {
                        "hits": hits,
                        "source_mode": "imported" if os.getenv("NY_UNCLAIMED_DATA_FILE") else "demo_only",
                        "agent": AGENT.explain_mode(),
                    },
                )

            if path == "/api/claims":
                profile = body.get("profile") or {}
                hit = body.get("hit") or {}
                claim = EVENTS.create_claim(
                    {
                        "business_name": profile.get("legal_name"),
                        "business_id": profile.get("id"),
                        "match_name": hit.get("found_name"),
                        "property_type": hit.get("property_type"),
                        "city": hit.get("city"),
                        "zip": hit.get("zip"),
                        "amount_cents": hit.get("amount_cents"),
                        "confidence": hit.get("confidence"),
                        "status": "MATCH_FOUND",
                        "hit": hit,
                        "profile": profile,
                        "demo_only": True,
                        "next_action": "Prepare claim form",
                    }
                )
                EVENTS.append_memory(
                    {
                        "claim_id": claim["id"],
                        "kind": "match_selected",
                        "summary": f"Selected match {hit.get('found_name')}",
                        "reason": ", ".join(hit.get("reasons") or []) or "User selected search hit",
                        "actor": "user",
                        "source": hit.get("source", "search"),
                    }
                )
                return self._json(201, {"claim": claim})

            if path == "/api/forms/prepare":
                claim_id = body.get("claim_id")
                claim = EVENTS.get_claim(claim_id)
                if not claim:
                    return self._json(404, {"error": "claim_not_found"})
                profile = body.get("profile") or claim.get("profile") or {}
                hit = body.get("hit") or claim.get("hit") or {}
                prepared = AGENT.prepare(profile, hit)
                fields = prepared["fields"]
                form = EVENTS.save_form(
                    {
                        "claim_id": claim_id,
                        "fields": fields,
                        "status": "FORM_READY",
                        "validation_errors": prepared["validation_errors"],
                        "agency": "NY Office of Unclaimed Funds (mock)",
                        "form_hash": None,
                        "approved": False,
                    }
                )
                EVENTS.update_claim(
                    claim_id,
                    {
                        "status": "FORM_READY",
                        "next_action": (
                            "Resolve conflicts before approval"
                            if prepared["validation_errors"]
                            else "Approve and submit form"
                        ),
                    },
                )
                EVENTS.append_event(
                    {
                        "claim_id": claim_id,
                        "from_status": "MATCH_FOUND",
                        "to_status": "FORM_READY",
                        "actor": "agent",
                        "source": "form_prepare",
                        "note": "Form prepared with provenance",
                    }
                )
                EVENTS.append_memory(
                    {
                        "claim_id": claim_id,
                        "kind": "form_prepared",
                        "summary": "Prepared claim form with field provenance",
                        "reason": (
                            "Conflicts require confirmation"
                            if prepared["validation_errors"]
                            else "All required fields present"
                        ),
                        "validation_errors": prepared["validation_errors"],
                        "actor": "agent",
                        "source": "forms.provenance",
                    }
                )
                return self._json(200, {"form": form, "claim": EVENTS.get_claim(claim_id)})

            if path == "/api/forms/save":
                claim_id = body.get("claim_id")
                fields_raw = body.get("fields") or []
                objs = [FormField(**f) for f in fields_raw]
                errors = validate_fields(objs)
                fh = form_hash(objs) if not errors else None
                form = EVENTS.save_form(
                    {
                        "claim_id": claim_id,
                        "fields": [f.__dict__ for f in objs],
                        "status": "FORM_READY",
                        "validation_errors": errors,
                        "agency": body.get("agency") or "NY Office of Unclaimed Funds (mock)",
                        "form_hash": fh,
                        "approved": False,
                    }
                )
                EVENTS.update_claim(
                    claim_id,
                    {
                        "form_hash": fh,
                        "next_action": "Resolve conflicts before approval" if errors else "Approve and submit form",
                    },
                )
                return self._json(200, {"form": form, "ok": not errors, "errors": errors})

            if path == "/api/forms/approve":
                claim_id = body.get("claim_id")
                form = EVENTS.get_form(claim_id)
                if not form:
                    return self._json(404, {"error": "form_not_found"})
                objs = [FormField(**f) for f in form["fields"]]
                errors = validate_fields(objs)
                if errors:
                    return self._json(400, {"error": "form_not_ready", "errors": errors})
                if not body.get("approved"):
                    return self._json(400, {"error": "authorization_required"})
                fh = form_hash(objs)
                result = EVENTS.transition_claim(
                    claim_id=claim_id,
                    to_status="USER_APPROVED",
                    actor="user",
                    evidence_kind=None,
                    source="user_approval",
                    note="Authorized representative approved immutable form snapshot",
                    claim_updates={"form_hash": fh, "next_action": "Submit to demo portal"},
                )
                form = EVENTS.save_form({**form, "approved": True, "form_hash": fh, "status": "USER_APPROVED"})
                return self._json(200, {"form": form, **result})

            if path == "/api/claims/submit":
                claim_id = body.get("claim_id")
                claim = EVENTS.get_claim(claim_id)
                form = EVENTS.get_form(claim_id)
                if not claim or not form:
                    return self._json(404, {"error": "claim_or_form_not_found"})
                if claim["status"] != "USER_APPROVED":
                    return self._json(409, {"error": f"Claim must be USER_APPROVED, got {claim['status']}"})
                objs = [FormField(**f) for f in form["fields"]]
                readback = {f.field: f.value for f in objs}
                submitted = AGENT.tools.daytona_fill_and_submit(
                    approved_fields=[f.__dict__ for f in objs],
                    browser_readback=readback,
                    claim_id=claim_id,
                )
                if not submitted.get("ok"):
                    return self._json(409, {"error": "readback_mismatch", "details": submitted})
                confirmation_id = submitted["confirmation_id"]
                EVENTS.transition_claim(
                    claim_id=claim_id,
                    to_status="SUBMITTED",
                    actor="user",
                    evidence_kind="submission",
                    source="daytona_mock_portal",
                    reference=confirmation_id,
                    note="Sandbox browser submitted approved form values",
                    payload={"submit_log": body.get("submit_log") or []},
                )
                result = EVENTS.transition_claim(
                    claim_id=claim_id,
                    to_status="CLAIM_RECEIVED",
                    actor="mock_portal",
                    evidence_kind="agency_receipt",
                    source="mock_ny_portal",
                    reference=confirmation_id,
                    note="Mock agency receipt recorded",
                    claim_updates={"confirmation_id": confirmation_id},
                )
                return self._json(200, {"submission": submitted, **result, "bundle": _claim_bundle(claim_id)})

            if path == "/api/claims/advance":
                claim_id = body.get("claim_id")
                claim = EVENTS.get_claim(claim_id)
                if not claim:
                    return self._json(404, {"error": "claim_not_found"})
                action = body.get("action") or "agency"
                status = claim["status"]

                if action == "agency":
                    sequence = {
                        "CLAIM_RECEIVED": ("PROCESSING", None, "Agency moved claim to processing"),
                        "PROCESSING": ("APPROVED", "agency_approval", "Mock agency approval notice"),
                        "APPROVED": ("PAYMENT_ISSUED", "agency_payment_issued", "Mock agency payment issued"),
                    }
                    if status == "CLAIM_RECEIVED" and body.get("reject"):
                        result = EVENTS.transition_claim(
                            claim_id=claim_id,
                            to_status="REJECTED",
                            actor="mock_agency",
                            evidence_kind=None,
                            source="mock_ny_portal",
                            note=body.get("note") or "Identity documentation insufficient (demo rejection)",
                        )
                        return self._json(200, result)
                    if status == "CLAIM_RECEIVED" and body.get("needs_docs"):
                        result = EVENTS.transition_claim(
                            claim_id=claim_id,
                            to_status="NEEDS_DOCS",
                            actor="mock_agency",
                            evidence_kind=None,
                            source="mock_ny_portal",
                            note=body.get("note") or "Agency requested authorization letter (demo)",
                        )
                        return self._json(200, result)
                    if status not in sequence:
                        return self._json(409, {"error": f"Cannot advance agency from {status}"})
                    to_status, evidence_kind, note = sequence[status]
                    result = EVENTS.transition_claim(
                        claim_id=claim_id,
                        to_status=to_status,
                        actor="mock_agency",
                        evidence_kind=evidence_kind,
                        source="mock_ny_portal",
                        reference=claim.get("confirmation_id"),
                        note=note,
                    )
                    return self._json(200, result)

                if action == "bank":
                    if status != "PAYMENT_ISSUED":
                        return self._json(409, {"error": "Bank confirmation requires PAYMENT_ISSUED"})
                    amount = claim.get("amount_cents") or 0
                    bank = AGENT.tools.match_bank_transaction(
                        "acct_demo",
                        amount_cents=amount,
                        confirmation_id=claim.get("confirmation_id") or claim_id,
                        emit_demo_deposit=True,
                    )
                    if not bank.get("matched"):
                        return self._json(409, {"error": "bank_not_matched", "details": bank})
                    result = EVENTS.transition_claim(
                        claim_id=claim_id,
                        to_status="PAYMENT_CONFIRMED",
                        actor="mock_bank",
                        evidence_kind="bank_deposit",
                        source="synthetic_bank",
                        reference=claim.get("confirmation_id"),
                        note="Synthetic demo bank deposit matched",
                        payload=bank,
                    )
                    return self._json(200, {**result, "bank": bank})

                if action == "stop":
                    result = EVENTS.transition_claim(
                        claim_id=claim_id,
                        to_status="STOPPED_BY_USER",
                        actor="user",
                        evidence_kind=None,
                        source="ui",
                        note="User stopped the claim",
                    )
                    return self._json(200, result)

                if action == "resume_docs":
                    if status != "NEEDS_DOCS":
                        return self._json(409, {"error": "Claim is not NEEDS_DOCS"})
                    result = EVENTS.transition_claim(
                        claim_id=claim_id,
                        to_status="PROCESSING",
                        actor="user",
                        evidence_kind=None,
                        source="ui",
                        note="User provided requested documents (demo)",
                    )
                    return self._json(200, result)

                return self._json(400, {"error": f"Unknown action {action}"})

            if path == "/api/events":
                event = body
                if event.get("from_status") and event.get("to_status"):
                    result = can_transition(event["from_status"], event["to_status"], event.get("evidence_kind"))
                    if not result.ok:
                        return self._json(409, {"error": result.error})
                return self._json(201, EVENTS.append_event(event))

            if path == "/api/demo/reset":
                seed = _load_seed()
                payload = EVENTS.reset_demo(seed)
                return self._json(200, {"ok": True, "tracker": EVENTS.tracker(), "seed_meta": payload.get("meta")})

            return self._json(404, {"error": "not_found"})
        except KeyError as exc:
            return self._json(404, {"error": str(exc)})
        except FileNotFoundError as exc:
            return self._json(503, {"error": str(exc), "hint": "Configure provider/data file or use demo mode"})
        except Exception as exc:  # local API must return useful UI errors
            return self._json(400, {"error": str(exc)})


def main() -> None:
    # Ensure seeded demo exists for first run / empty state.
    data_file = Path(os.environ.get("MONEYFINDER_EVENT_FILE", "data/moneyfinder-events.json"))
    if not data_file.exists() or not json.loads(data_file.read_text() or "{}").get("claims"):
        if SEED_PATH.exists():
            EVENTS.reset_demo(_load_seed())
    port = int(os.environ.get("PORT", "4173"))
    print(f"MoneyFinder running at http://localhost:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
