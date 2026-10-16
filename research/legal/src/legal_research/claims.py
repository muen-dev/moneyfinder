"""How many taxpayers claim each credit, from NYS Tax Department datasets on data.ny.gov.

Few claimants for a credit that many businesses could qualify for is the clearest sign of a niche
worth surfacing. Datasets lag: the newest tax year is usually two or three years back.
"""

import re

from .catalog import Dataset, Program
from .providers import Providers

COLUMNS = "tax_year,tax_article,credit_name,usage_restriction,external_agency,number_of_taxpayers,amount_of_credit"
HISTORY_YEARS = 5
MATCH_THRESHOLD = 0.6

# Agencies that certify a business before it can claim (the dataset's external_agency column).
AGENCIES = {
    "ESD": "Empire State Development",
    "DOL": "NYS Department of Labor",
    "DEC": "NYS Department of Environmental Conservation",
    "OPRHP": "NYS Office of Parks, Recreation and Historic Preservation",
    "OASAS": "NYS Office of Addiction Services and Supports",
    "DHS": "NYS Division of Homeland Security and Emergency Services",
    "AGM": "NYS Department of Agriculture and Markets",
    "DHCR": "NYS Homes and Community Renewal",
    "NYSERDA": "NYSERDA",
    "OCFS": "NYS Office of Children and Family Services",
    "DCJS": "NYS Division of Criminal Justice Services",
}

STOP = {"tax", "taxes", "credit", "credits", "program", "the", "for", "of", "a", "an", "and", "to", "ny", "nys", "new", "york", "state", "empire"}
SPELLING = {"childcare": "child care", "post-production": "post production", "start-up": "start up"}


def fetch(providers: Providers, dataset: Dataset) -> list[dict]:
    return providers.socrata(dataset.host, dataset.dataset, {"$select": COLUMNS, "$limit": "20000"})


def _int(value) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None  # blank: suppressed for taxpayer confidentiality, or not reported


def summarize(rows: list[dict], dataset: Dataset) -> dict[str, dict]:
    """One entry per credit name: newest year with figures, claimants, dollars and a short history.

    Article 9-A and Article 22 rows for the same year are added together.
    """
    years: dict[str, dict[int, dict]] = {}
    meta: dict[str, dict] = {}
    for row in rows:
        name = " ".join(str(row.get("credit_name") or "").split())
        year = _int(row.get("tax_year"))
        if not name or year is None:
            continue
        info = meta.setdefault(name, {"articles": set(), "agency": None, "usage": None})
        if row.get("tax_article"):
            info["articles"].add(str(row["tax_article"]))
        agency = (row.get("external_agency") or "").strip()
        if agency and agency not in ("-", "N/A"):
            info["agency"] = agency
        info["usage"] = row.get("usage_restriction") or info["usage"]
        slot = years.setdefault(name, {}).setdefault(year, {"taxpayers": None, "amount": None})
        for key, column in (("taxpayers", "number_of_taxpayers"), ("amount", "amount_of_credit")):
            if (value := _int(row.get(column))) is not None:
                slot[key] = (slot[key] or 0) + value

    out = {}
    for name, by_year in years.items():
        reported = sorted((y for y, v in by_year.items() if v["taxpayers"] is not None), reverse=True)
        latest = reported[0] if reported else max(by_year)
        figures = by_year[latest]
        taxpayers, amount = figures["taxpayers"], figures["amount"]
        agency = meta[name]["agency"]
        out[name] = {
            "credit_name": name,
            "dataset": dataset.id,
            "source": f"https://{dataset.host}/d/{dataset.dataset}",
            "latest_year": latest,
            "taxpayers": taxpayers,
            "amount": amount,
            "average": round(amount / taxpayers) if taxpayers and amount is not None else None,
            "usage": meta[name]["usage"],
            "certifying_agency": AGENCIES.get(agency, agency) if agency else None,
            "articles": sorted(meta[name]["articles"]),
            "history": [
                {"year": y, **by_year[y]} for y in sorted(by_year, reverse=True)[:HISTORY_YEARS]
            ],
        }
    return out


def tokens(name: str) -> frozenset[str]:
    text = name.lower().replace("&", " and ").replace("'", "").replace("’", "")
    for old, new in SPELLING.items():
        text = text.replace(old, new)
    return frozenset(w for w in re.findall(r"[a-z0-9]+", text) if w not in STOP)


def similarity(a: str, b: str) -> float:
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def attach(programs: list[Program], summaries: dict[str, dict]) -> list[dict]:
    """Attach claim summaries to programs. Returns the credits that matched no program (leads to look into).

    Names listed in a program's claims_names always match. The rest pair up greedily, best score first,
    so "Empire State film production credit" takes its own row before "independent film production" can.
    """
    taken: set[str] = set()
    for program in programs:
        for name in program.claims_names:
            if name in summaries:
                program.claims.append(summaries[name])
                taken.add(name)

    pairs = []
    for program in programs:
        if program.claims_names or program.jurisdiction != "NYS":
            continue
        names = [program.name, *program.aliases]
        for credit in summaries:
            if credit in taken:
                continue
            score = max(similarity(n, credit) for n in names)
            if score >= MATCH_THRESHOLD:
                pairs.append((score, program.id, credit))
    matched: set[str] = set()
    by_id = {p.id: p for p in programs}
    for score, pid, credit in sorted(pairs, key=lambda p: -p[0]):
        if pid in matched or credit in taken:
            continue
        by_id[pid].claims.append(summaries[credit] | {"match": round(score, 2)})
        matched.add(pid)
        taken.add(credit)
    return [s for name, s in sorted(summaries.items()) if name not in taken]
