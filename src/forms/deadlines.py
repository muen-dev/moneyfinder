"""Extract and normalize processing deadlines from claim/agency text."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


_RANGE = re.compile(
    r"(?P<lo>\d+)\s*(?:to|-)\s*(?P<hi>\d+)\s*(?P<unit>day|days|week|weeks)",
    re.IGNORECASE,
)
_SINGLE = re.compile(r"(?:within|up to)\s+(?P<n>\d+)\s*(?P<unit>day|days|week|weeks)", re.IGNORECASE)


@dataclass
class DeadlineWindow:
    expected_by: datetime
    label: str
    confidence: float


def extract_deadline(text: str, *, from_dt: datetime | None = None) -> DeadlineWindow | None:
    """Parse phrases like '2 to 4 weeks' or 'within 30 days' into expected_by UTC."""
    base = from_dt or datetime.now(timezone.utc)
    m = _RANGE.search(text or "")
    if m:
        hi = int(m.group("hi"))
        unit = m.group("unit").lower()
        delta = timedelta(weeks=hi) if unit.startswith("week") else timedelta(days=hi)
        return DeadlineWindow(expected_by=base + delta, label=m.group(0), confidence=0.9)
    m = _SINGLE.search(text or "")
    if m:
        n = int(m.group("n"))
        unit = m.group("unit").lower()
        delta = timedelta(weeks=n) if unit.startswith("week") else timedelta(days=n)
        return DeadlineWindow(expected_by=base + delta, label=m.group(0), confidence=0.85)
    return None
