"""Persistence boundary: JSON fallback now, SurrealDB implementation behind same API."""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class EventRepository:
    def save_profile(self, profile: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def append_event(self, event: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def events(self, claim_id: str | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError


class JsonEventRepository(EventRepository):
    """Local development repository with the same event shape as Surreal schema."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path or os.environ.get("MONEYFINDER_EVENT_FILE", "data/moneyfinder-events.json"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"profiles": [], "events": []}
        return json.loads(self.path.read_text())

    def _write(self, value: dict[str, Any]) -> None:
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(value, indent=2, default=str))
        temp.replace(self.path)

    def save_profile(self, profile: dict[str, Any]) -> dict[str, Any]:
        record = {**profile, "saved_at": now_iso()}
        with self._lock:
            data = self._read()
            data["profiles"].append(record)
            self._write(data)
        return record

    def append_event(self, event: dict[str, Any]) -> dict[str, Any]:
        record = {**event, "created_at": event.get("created_at") or now_iso()}
        with self._lock:
            data = self._read()
            data["events"].append(record)
            self._write(data)
        return record

    def events(self, claim_id: str | None = None) -> list[dict[str, Any]]:
        values = self._read()["events"]
        return [event for event in values if not claim_id or event.get("claim_id") == claim_id]


def repository() -> EventRepository:
    """Select JSON locally; a future SurrealRepository can be injected here."""
    return JsonEventRepository()
