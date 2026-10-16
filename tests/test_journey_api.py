"""API/state coverage for the rebuilt MoneyFinder journey."""

from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.persistence import JsonEventRepository  # noqa: E402
from src.pipeline.status import can_transition  # noqa: E402


class JourneyApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.event_file = Path(self.tmp.name) / "events.json"
        self.seed = json.loads((ROOT / "fixtures" / "demo-seed.json").read_text())
        repo = JsonEventRepository(self.event_file)
        repo.reset_demo(self.seed)

        import src.server as server

        self.server_mod = server
        server.EVENTS = repo
        self.httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self.tmp.cleanup()

    def _req(self, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        payload = json.dumps(body or {}).encode() if body is not None or method == "POST" else None
        headers = {"Content-Type": "application/json"} if payload is not None else {}
        conn.request(method, path, body=payload, headers=headers)
        resp = conn.getresponse()
        data = json.loads(resp.read().decode() or "{}")
        conn.close()
        return resp.status, data

    def test_tracker_seed_loads(self) -> None:
        status, data = self._req("GET", "/api/tracker")
        self.assertEqual(status, 200)
        self.assertGreaterEqual(data["summary"]["claims_total"], 2)
        self.assertFalse(data["surreal_live"])

    def test_conflict_blocks_approval(self) -> None:
        profile = {
            "entity_type": "business",
            "legal_name": "Example NYC Foods LLC",
            "dbas": ["Example Foods"],
            "business_type": "LLC",
            "addresses": [{"street": "123 Main", "city": "Brooklyn", "state": "NY", "zip": "11201", "current": True}],
            "authorized_representative": {"name": "Maria Alvarez", "role": "Managing Member"},
            "search_consent": True,
        }
        _, created = self._req(
            "POST",
            "/api/claims",
            {
                "profile": profile,
                "hit": {
                    "found_name": "Example Foods",
                    "property_type": "Uncashed vendor check",
                    "city": "Brooklyn",
                    "zip": "11201",
                    "amount_cents": 41200,
                    "confidence": 0.95,
                    "reasons": ["name"],
                    "source": "mock_ny_unclaimed",
                },
            },
        )
        claim_id = created["claim"]["id"]
        _, prepared = self._req("POST", "/api/forms/prepare", {"claim_id": claim_id, "profile": profile})
        self.assertTrue(prepared["form"]["validation_errors"])
        status, denied = self._req("POST", "/api/forms/approve", {"claim_id": claim_id, "approved": True})
        self.assertEqual(status, 400)
        self.assertEqual(denied["error"], "form_not_ready")

    def test_full_happy_path_and_bank_rail(self) -> None:
        profile = {
            "entity_type": "business",
            "legal_name": "Example NYC Foods LLC",
            "dbas": ["Example Foods"],
            "addresses": [{"city": "Brooklyn", "state": "NY", "zip": "11201", "current": True}],
            "authorized_representative": {"name": "Maria Alvarez", "role": "Managing Member"},
            "search_consent": True,
        }
        _, created = self._req(
            "POST",
            "/api/claims",
            {
                "profile": profile,
                "hit": {
                    "found_name": "Example Foods",
                    "property_type": "Uncashed vendor check",
                    "city": "Brooklyn",
                    "zip": "11201",
                    "amount_cents": 41200,
                    "confidence": 0.95,
                    "reasons": ["name"],
                    "source": "mock_ny_unclaimed",
                    "force_demo_conflict": False,
                },
            },
        )
        claim_id = created["claim"]["id"]
        _, prepared = self._req(
            "POST",
            "/api/forms/prepare",
            {
                "claim_id": claim_id,
                "profile": profile,
                "hit": {
                    **created["claim"]["hit"],
                    "force_demo_conflict": False,
                },
            },
        )
        fields = prepared["form"]["fields"]
        for field in fields:
            if field.get("requires_confirmation"):
                field["requires_confirmation"] = False
                field["edited_by_user"] = True
                field["source"] = "edited_by_user"
                field["conflicting_value"] = None
        self._req("POST", "/api/forms/save", {"claim_id": claim_id, "fields": fields})
        status, approved = self._req("POST", "/api/forms/approve", {"claim_id": claim_id, "approved": True})
        self.assertEqual(status, 200)
        self.assertEqual(approved["claim"]["status"], "USER_APPROVED")

        status, submitted = self._req("POST", "/api/claims/submit", {"claim_id": claim_id})
        self.assertEqual(status, 200)
        self.assertEqual(submitted["claim"]["status"], "CLAIM_RECEIVED")
        self.assertTrue(submitted["claim"]["confirmation_id"])

        # Agency rail
        for expected in ("PROCESSING", "APPROVED", "PAYMENT_ISSUED"):
            status, advanced = self._req("POST", "/api/claims/advance", {"claim_id": claim_id, "action": "agency"})
            self.assertEqual(status, 200)
            self.assertEqual(advanced["claim"]["status"], expected)

        # Bank rail only after payment issued
        status, bank = self._req("POST", "/api/claims/advance", {"claim_id": claim_id, "action": "bank"})
        self.assertEqual(status, 200)
        self.assertEqual(bank["claim"]["status"], "PAYMENT_CONFIRMED")
        self.assertTrue(bank["bank"]["transaction"]["synthetic"])

        status, bundle = self._req("GET", f"/api/claims/{claim_id}")
        self.assertEqual(status, 200)
        kinds = {e["kind"] for e in bundle["evidence"]}
        self.assertIn("agency_payment_issued", kinds)
        self.assertIn("bank_deposit", kinds)
        self.assertTrue(any(m.get("kind") == "status_transition" for m in bundle["memory_trail"]))

    def test_rejection_and_needs_docs(self) -> None:
        claim_id = "claim_demo_vendor_check"
        status, needs = self._req(
            "POST",
            "/api/claims/advance",
            {"claim_id": claim_id, "action": "agency", "needs_docs": True},
        )
        self.assertEqual(status, 200)
        self.assertEqual(needs["claim"]["status"], "NEEDS_DOCS")

        # Reset seed and reject
        self._req("POST", "/api/demo/reset", {})
        status, rejected = self._req(
            "POST",
            "/api/claims/advance",
            {"claim_id": claim_id, "action": "agency", "reject": True},
        )
        self.assertEqual(status, 200)
        self.assertEqual(rejected["claim"]["status"], "REJECTED")

    def test_illegal_transition_still_blocked(self) -> None:
        self.assertFalse(can_transition("MATCH_FOUND", "PAYMENT_CONFIRMED", "bank_deposit").ok)


if __name__ == "__main__":
    unittest.main()
