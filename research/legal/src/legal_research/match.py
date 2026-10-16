"""Match a research/company profile to catalog programs, using the niches' NAICS prefixes and profile_keywords.

Niche-specific credits come first, fewest claimants first. Credits most employers can claim (benefits,
accessibility, targeted hiring) follow, ranked lower. Matching is a lead for a person to check, not a ruling.
"""

import re

from . import store

# Niches most employers can fall into; their programs are listed after the niche-specific ones.
BROAD_NICHES = frozenset({
    "employee_benefits", "accessibility_safety", "hiring_veterans", "hiring_disabilities", "hiring_youth",
    "hiring_recovery", "hiring_targeted_groups", "training_apprenticeship",
})
CLOSED_NICHES = frozenset({"legacy_zones"})  # closed to new businesses

# Profile fields whose text is matched against profile_keywords: what the business is, then softer signals.
CORE_FIELDS = ("legal_name", "dba", "industry", "naics", "description", "summary", "products_services",
               "nyc_borough", "nyc_licenses", "ownership_certifications")
SIGNAL_FIELDS = ("incentive_signals", "hiring_signals", "rd_tech_signals", "expansion_signals")
# A non-empty signal field is evidence for a niche on its own.
SIGNAL_NICHES = {"rd_tech_signals": "research_development", "expansion_signals": "growth_esd"}
FIELD_LABELS = {"naics": "NAICS", "nyc_borough": "NYC borough", "nyc_licenses": "NYC licenses",
                "rd_tech_signals": "R&D signals", "products_services": "Products and services", "dba": "DBA"}


def match_programs(profile: dict, catalog: dict | None = None) -> list[dict]:
    """Programs this profile may qualify for, best leads first. Each has why/evidence, claimants and PDF forms."""
    catalog = catalog if catalog is not None else store.read_catalog()
    if not catalog or not profile:
        return []
    niches = {n["id"]: n for n in catalog.get("niches", [])}
    hits = {nid: _niche_evidence(profile, niche) for nid, niche in niches.items()}
    hits = {nid: ev for nid, ev in hits.items() if ev}

    matches = []
    for program in catalog.get("programs", []):
        tags = set(program.get("niches") or [])
        if not tags or tags & CLOSED_NICHES:
            continue
        industry = {t for t in tags if niches.get(t, {}).get("naics")}
        matched = [t for t in program["niches"] if t in hits]
        if industry and not industry <= set(matched):
            continue  # an industry credit needs every industry it names (e.g. semiconductor R&D needs both)
        if matched:
            tier, evidence = "niche" if set(matched) - BROAD_NICHES else "broad", [e for t in matched for e in hits[t]]
        elif tags <= BROAD_NICHES:
            tier, evidence = "broad", []
        else:
            continue
        matches.append(_entry(program, tier, matched, evidence, niches))
    matches.sort(key=_rank)
    return matches


def _niche_evidence(profile: dict, niche: dict) -> list[dict]:
    evidence = []
    for code, source in _naics_codes(profile):
        prefix = next((p for p in niche.get("naics", []) if code.startswith(p)), None)
        if prefix:
            evidence.append({"niche": niche["id"], "kind": "naics", "field": "naics", "value": code,
                             "keyword": prefix, "source": source})
            break
    # Broad niches' keywords ("benefits") are common words in a description; only signals count for them.
    names = SIGNAL_FIELDS + ("ownership_certifications",) if niche["id"] in BROAD_NICHES else CORE_FIELDS + SIGNAL_FIELDS
    for name in names:
        for text, source in _texts(profile, name):
            keyword = next((k for k in niche.get("profile_keywords", []) if _keyword_re(k).search(text)), None)
            if keyword:
                kind = "keyword" if name in CORE_FIELDS else "signal"
                evidence.append({"niche": niche["id"], "kind": kind, "field": name, "value": text[:160],
                                 "keyword": keyword, "source": source})
                break
    for name, nid in SIGNAL_NICHES.items():
        if nid == niche["id"] and not any(e["field"] == name for e in evidence):
            first = next(iter(_texts(profile, name)), None)
            if first:
                evidence.append({"niche": nid, "kind": "signal", "field": name, "value": first[0][:160],
                                 "keyword": "", "source": first[1]})
    return evidence


def _entry(program: dict, tier: str, matched: list[str], evidence: list[dict], niches: dict) -> dict:
    facts = program.get("facts") or {}
    claims = program.get("claims") or []
    claimants = sum(c.get("taxpayers") or 0 for c in claims) if claims else None
    amount = sum(c.get("amount") or 0 for c in claims) if claims else None
    return {
        "id": program["id"],
        "name": program["name"],
        "jurisdiction": program.get("jurisdiction", ""),
        "agency": program.get("agency", ""),
        "kind": program.get("kind", ""),
        "url": program.get("url", ""),
        "status": program.get("status", "unknown"),
        "status_note": program.get("status_note", ""),
        "requires_preapproval": bool(program.get("requires_preapproval")),
        "tier": tier,
        "niches": [{"id": n, "label": niches.get(n, {}).get("label", n)} for n in (matched or program["niches"])],
        "why": _why(tier, matched, evidence, niches),
        "evidence": evidence,
        "score": sum({"naics": 3, "keyword": 2, "signal": 1}[e["kind"]] for e in evidence),
        "claimants": claimants,
        "claimed_amount": amount,
        "claims_year": max((c.get("latest_year") or 0 for c in claims), default=None) or None,
        "amount": facts.get("amount", ""),
        "eligibility": facts.get("eligibility", ""),
        "forms": [
            {"label": _form_label(f), "code": f.get("code", ""), "url": f["pdf"], "instructions": f.get("instructions")}
            for f in facts.get("forms", []) if f.get("pdf")
        ],
    }


def _why(tier: str, matched: list[str], evidence: list[dict], niches: dict) -> list[str]:
    if not evidence:
        return ["Most employers can claim this; check the eligibility rules."]
    lines = []
    for e in evidence:
        label = niches.get(e["niche"], {}).get("label", e["niche"])
        if e["kind"] == "naics":
            lines.append(f"NAICS {e['value']} is in {label} ({e['keyword']}*)")
        elif e["keyword"]:
            lines.append(f"{_field(e['field'])} mentions “{e['keyword']}” ({label}): {e['value']}")
        else:
            lines.append(f"{_field(e['field'])} found ({label}): {e['value']}")
    return lines


def _field(name: str) -> str:
    return FIELD_LABELS.get(name) or name.replace("_", " ").capitalize()


def _rank(m: dict) -> tuple:
    strong = any(e["kind"] in ("naics", "keyword") for e in m["evidence"])
    return (
        m["tier"] != "niche",
        m["status"] == "expired",
        not strong,
        m["claimants"] if m["claimants"] is not None else float("inf"),
        -m["score"],
        m["name"],
    )


def _form_label(form: dict) -> str:
    code = form.get("code", "")
    who = {"CT": "corporations", "IT": "individuals, partnerships and LLCs"}.get(code.split("-")[0])
    if code.isdigit():
        return f"IRS Form {code}"
    return f"{code} ({who})" if who else code or "Form"


def _naics_codes(profile: dict) -> list[tuple[str, str]]:
    codes = []
    for value, source in _claims(profile, "naics"):
        code = value.get("code") if isinstance(value, dict) else value
        code = re.sub(r"\D", "", str(code or ""))
        if code:
            codes.append((code, source))
    return codes


def _texts(profile: dict, name: str) -> list[tuple[str, str]]:
    out = []
    for value, source in _claims(profile, name):
        if isinstance(value, dict):  # news-like items: the title says it; snippets are page noise
            text = " ".join(str(value.get(k) or "") for k in ("title", "name", "code") if value.get(k))
        else:
            text = str(value)
        if text.strip():
            out.append((text.strip(), source))
    return out


def _claims(profile: dict, name: str) -> list[tuple[object, str]]:
    """(value, first source url) for a field, from a research/company profile or a flat {field: value} dict."""
    fields = profile.get("fields")
    if isinstance(fields, dict):
        out = []
        for claim in fields.get(name) or []:
            sources = claim.get("sources") or [{}]
            out.append((claim.get("value"), sources[0].get("url", "")))
        return out
    value = profile.get(name)
    if value in (None, "", []):
        return []
    return [(v, "") for v in (value if isinstance(value, list) else [value])]


_KEYWORD_CACHE: dict[str, re.Pattern] = {}


def _keyword_re(keyword: str) -> re.Pattern:
    """Whole word (plural allowed); stems of 6+ letters ('manufactur') also match as a prefix; short
    all-caps acronyms (ADA, AED) are case-sensitive."""
    if keyword not in _KEYWORD_CACHE:
        stem = len(keyword) >= 6 and keyword.isalpha() and keyword.islower()
        tail = r"\w*" if stem else r"(?:s|es)?\b"
        flags = 0 if keyword.isupper() and len(keyword) <= 4 else re.IGNORECASE
        _KEYWORD_CACHE[keyword] = re.compile(rf"(?<!\w){re.escape(keyword)}{tail}", flags)
    return _KEYWORD_CACHE[keyword]
