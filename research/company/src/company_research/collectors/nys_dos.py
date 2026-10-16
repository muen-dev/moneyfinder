"""NYS Department of State entity records, from the 'Active Corporations' open dataset on data.ny.gov.

The dataset has no website column, so matches are by name; only exact (suffix-insensitive) name
matches are reported with high confidence.
"""

from ..enrich import name_key, name_similarity, name_variants, soql_prefix
from ..profile import CollectorResult
from ..providers import now
from . import Context, fact

NAME = "nys_dos"
HOST = "data.ny.gov"
DATASET = "n9v6-gdp6"
PAGE = "https://data.ny.gov/Economic-Development/Active-Corporations-Beginning-1800/n9v6-gdp6"


def collect(ctx: Context) -> CollectorResult:
    result = CollectorResult(NAME)
    rows: dict[str, dict] = {}
    names = _query_names(ctx)
    # Exact spellings first ('ACME, INC.', 'ACME LLC', ...); a bare prefix can return dozens of
    # per-location LLCs before the parent entity.
    variants = sorted({v for name in names for v in name_variants(name)})
    if variants:
        quoted = ", ".join(f"'{v}'" for v in variants[:60])
        for row in ctx.providers.socrata(HOST, DATASET, {"$where": f"current_entity_name in ({quoted})", "$limit": "20"}):
            rows.setdefault(row.get("dos_id", ""), row)
    if not rows:
        for name in names:
            if prefix := soql_prefix(name):
                params = {"$where": f"current_entity_name like '{prefix}%'", "$limit": "50"}
                for row in ctx.providers.socrata(HOST, DATASET, params):
                    rows.setdefault(row.get("dos_id", ""), row)
    ranked = sorted(
        ((max(name_similarity(row.get("current_entity_name", ""), n) for n in ctx.names or [ctx.name]), row) for row in rows.values()),
        key=lambda pair: (-pair[0], pair[1].get("initial_dos_filing_date", "")),
    )
    exact = [row for score, row in ranked if score >= 0.99]
    if exact:
        picks = [(row, 0.85 if len(exact) == 1 else 0.6, "" if len(exact) == 1 else "several entities share this name") for row in exact[:3]]
    elif ranked and ranked[0][0] >= 0.6:
        picks = [(ranked[0][1], 0.35, "closest name match, not exact")]
    else:
        result.error = "no matching NY entity" if not rows else f"{len(rows)} similarly named entities, none matching"
        return result

    at = now()
    for row, confidence, note in picks:
        url = f"https://{HOST}/resource/{DATASET}.json?dos_id={row.get('dos_id', '')}"

        def add(field_name, value, conf=confidence):
            if value:
                result.facts.append(fact(field_name, value, url, f"socrata:{HOST}", at, conf, NAME, note))

        add("legal_name", row.get("current_entity_name"))
        add("entity_type", (row.get("entity_type") or "").title())
        add("state_of_formation", (row.get("jurisdiction") or "").title())
        add("county", row.get("county"))
        add("ny_dos_id", row.get("dos_id"))
        add("ny_dos_filing_date", (row.get("initial_dos_filing_date") or "")[:10])
    result.context["related_entities"] = len(rows)
    return result


def _query_names(ctx: Context) -> list[str]:
    """Distinct name prefixes to search, so 'Joe's Pizza' and 'Joes Pizza LLC' share one query."""
    seen, names = set(), []
    for name in ctx.names or [ctx.name]:
        key = name_key(name)
        if key and key not in seen:
            seen.add(key)
            names.append(name)
    return names[:3]
