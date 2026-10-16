"""Match scoring for NY unclaimed property candidates."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MatchScore:
    confidence: float
    reasons: list[str]


def score_match(
    *,
    query_names: list[str],
    found_name: str,
    query_city: str | None,
    found_city: str | None,
    query_zip: str | None,
    found_zip: str | None,
) -> MatchScore:
    reasons: list[str] = []
    score = 0.0
    found_cf = found_name.casefold()

    for q in query_names:
        q_cf = q.casefold()
        if q_cf == found_cf:
            score += 0.55
            reasons.append("Exact name match")
            break
        if q_cf in found_cf or found_cf in q_cf:
            score += 0.35
            reasons.append("Partial name match")
            break

    if query_city and found_city and query_city.casefold() == found_city.casefold():
        score += 0.2
        reasons.append("City match")

    if query_zip and found_zip and query_zip[:5] == found_zip[:5]:
        score += 0.25
        reasons.append("ZIP match")

    return MatchScore(confidence=min(score, 0.99), reasons=reasons or ["Weak name similarity"])
