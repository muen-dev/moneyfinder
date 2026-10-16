"""Small local API for the domain-first MoneyFinder journey.

Run from the repository root:
    python3 -m src.server

The UI talks to this boundary instead of owning search and event state.
Company research is demo-safe by default; set COMPANY_RESEARCH_LIVE=1 only
after the research package dependencies and provider keys are configured.
"""

from __future__ import annotations

import json
import os
import sys
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


def research_domain(domain: str) -> dict:
    if not domain or "." not in domain:
        raise ValueError("A public business domain is required")
    if os.environ.get("COMPANY_RESEARCH_LIVE") != "1":
        return _demo_research(domain)
    company_root = ROOT / "research" / "company" / "src"
    sys.path.insert(0, str(company_root))
    from company_research.pipeline import research  # type: ignore

    return research(domain, out_dir=ROOT / "data" / "company-research" / domain)


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
