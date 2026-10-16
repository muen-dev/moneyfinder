"""Mock agency status timeline for hackathon demos."""

from __future__ import annotations

from datetime import datetime, timezone

from .base import AgencyStatus


class MockAgencyStatusProvider:
    """Advances status based on a simple step map keyed by confirmation_id."""

    def __init__(self) -> None:
        self._state: dict[str, str] = {}

    def seed(self, confirmation_id: str, status: str = "CLAIM_RECEIVED") -> None:
        self._state[confirmation_id] = status

    def advance(self, confirmation_id: str) -> AgencyStatus:
        order = [
            "CLAIM_RECEIVED",
            "PROCESSING",
            "APPROVED",
            "PAYMENT_ISSUED",
        ]
        current = self._state.get(confirmation_id, "CLAIM_RECEIVED")
        try:
            nxt = order[min(order.index(current) + 1, len(order) - 1)]
        except ValueError:
            nxt = "PROCESSING"
        self._state[confirmation_id] = nxt
        return self.get_status(confirmation_id)

    def get_status(self, confirmation_id: str) -> AgencyStatus:
        status = self._state.get(confirmation_id, "PROCESSING")
        return AgencyStatus(
            status=status,
            reference=confirmation_id,
            checked_at=datetime.now(timezone.utc),
            raw={"provider": "mock_ny_portal", "confirmation_id": confirmation_id},
        )
