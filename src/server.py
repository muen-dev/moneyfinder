"""Small local API for the domain-first MoneyFinder journey.

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
from urllib.parse import urlparse

from .persistence import repository
from .pipeline.status import can_transition
from .profile_mapper import company_profile_to_search_profile
from .agent.orchestrator import MoneyFinderAgent

ROOT = Path(__file__).resolve().parents[1]
UI_ROOT = ROOT / "ui"
UI_ENTRY = UI_ROOT / "domain.html"
COMPANY_PROJECT = ROOT / "research" / "company"
# Same env var research/company's config uses, so the server reads where the CLI writes.
COMPANY_DATA_DIR = Path(os.environ.get("COMPANY_DATA_DIR", COMPANY_PROJECT / "data"))
COMPANY_RESEARCH_TIMEOUT_S = int(os.environ.get("COMPANY_RESEARCH_TIMEOUT", "240"))
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

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            self._json(200, {"ok": True, "money_source": "imported" if os.getenv("NY_UNCLAIMED_DATA_FILE") else "demo"})
            return
        if path == "/api/events":
            self._json(200, EVENTS.events())
            return
        if path in ("/", "/index.html"):
            content = UI_ENTRY.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return
        self._json(404, {"error": "not_found"})

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
                saved = EVENTS.save_profile(mapped)
                return self._json(200, {"profile": saved})
            if path == "/api/search":
                profile = body.get("profile") or {}
                hits = AGENT.build_and_search(profile)
                return self._json(200, {
                    "hits": hits,
                    "source_mode": "imported" if os.getenv("NY_UNCLAIMED_DATA_FILE") else "demo_only",
                    "agent": AGENT.explain_mode(),
                })
            if path == "/api/events":
                event = body
                if event.get("from_status") and event.get("to_status"):
                    result = can_transition(event["from_status"], event["to_status"], event.get("evidence_kind"))
                    if not result.ok:
                        return self._json(409, {"error": result.error})
                return self._json(201, EVENTS.append_event(event))
            return self._json(404, {"error": "not_found"})
        except FileNotFoundError as exc:
            return self._json(503, {"error": str(exc), "hint": "Configure provider/data file or use demo mode"})
        except Exception as exc:  # local API must return useful UI errors
            return self._json(400, {"error": str(exc)})


def main() -> None:
    port = int(os.environ.get("PORT", "4173"))
    print(f"MoneyFinder running at http://localhost:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
