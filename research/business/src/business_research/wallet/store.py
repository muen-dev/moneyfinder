"""Per-business Wallet persistence (JSON, Surreal-shaped claims/forms/events)."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from .. import config, ids
from . import _repo

_repo.ensure_repo_on_path()

from src.persistence import JsonEventRepository, new_id, now_iso  # noqa: E402


class BusinessWalletStore:
    """One JsonEventRepository file per business_id under DATA_DIR/<id>/wallet-events.json."""

    def __init__(self, business_id: str, root: Path | None = None):
        self.business_id = ids.check(business_id)
        self.root = Path(root or config.DATA_DIR) / self.business_id
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "wallet-events.json"
        self.repo = JsonEventRepository(self.path)
        self._lock = threading.Lock()
        self.meta_path = self.root / "wallet-meta.json"

    def _meta(self) -> dict[str, Any]:
        if not self.meta_path.exists():
            return {"opportunities": [], "fill_jobs": []}
        try:
            data = json.loads(self.meta_path.read_text())
        except (OSError, ValueError):
            return {"opportunities": [], "fill_jobs": []}
        data.setdefault("opportunities", [])
        data.setdefault("fill_jobs", [])
        return data

    def _write_meta(self, data: dict[str, Any]) -> None:
        tmp = self.meta_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, default=str))
        tmp.replace(self.meta_path)

    def save_opportunities(self, opportunities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        with self._lock:
            meta = self._meta()
            stamped = []
            for row in opportunities:
                item = {
                    **row,
                    "business_id": self.business_id,
                    "saved_at": now_iso(),
                    "wallet_id": row.get("wallet_id") or new_id("opp"),
                }
                stamped.append(item)
            meta["opportunities"] = stamped
            self._write_meta(meta)
            return stamped

    def opportunities(self) -> list[dict[str, Any]]:
        return list(self._meta().get("opportunities") or [])

    def get_opportunity(self, opportunity_id: str) -> dict[str, Any] | None:
        for row in self.opportunities():
            if row.get("wallet_id") == opportunity_id or row.get("id") == opportunity_id:
                return row
        return None

    def save_fill_job(self, job: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            meta = self._meta()
            record = {**job, "id": job.get("id") or new_id("fill"), "updated_at": now_iso()}
            jobs = [j for j in meta["fill_jobs"] if j.get("id") != record["id"]]
            jobs.append(record)
            meta["fill_jobs"] = jobs
            self._write_meta(meta)
            return record

    def get_fill_job(self, job_id: str) -> dict[str, Any] | None:
        for job in self._meta().get("fill_jobs") or []:
            if job.get("id") == job_id:
                return job
        return None

    def fill_jobs_for_claim(self, claim_id: str) -> list[dict[str, Any]]:
        return [j for j in self._meta().get("fill_jobs") or [] if j.get("claim_id") == claim_id]

    def tracker(self) -> dict[str, Any]:
        data = self.repo.tracker()
        data["business_id"] = self.business_id
        data["opportunities"] = self.opportunities()
        data["fill_jobs"] = self._meta().get("fill_jobs") or []
        return data

    def claims(self) -> list[dict[str, Any]]:
        return [c for c in self.repo.claims() if c.get("business_id") == self.business_id]

    def get_claim(self, claim_id: str) -> dict[str, Any] | None:
        claim = self.repo.get_claim(claim_id)
        if claim and claim.get("business_id") == self.business_id:
            return claim
        return None

    def claim_bundle(self, claim_id: str) -> dict[str, Any] | None:
        claim = self.get_claim(claim_id)
        if not claim:
            return None
        return {
            "claim": claim,
            "form": self.repo.get_form(claim_id),
            "events": self.repo.events(claim_id),
            "evidence": self.repo.evidence(claim_id),
            "memory_trail": self.repo.memory(claim_id),
            "fill_jobs": self.fill_jobs_for_claim(claim_id),
            "business_id": self.business_id,
            "persistence": "json",
            "surreal_live": False,
        }
