"""Push a per-business dossier (moneyfinder.dossier/v1, written by research/) into SurrealDB.

One push, one transaction, safe to repeat:
  business:<slug>         name, website, naics, ... + profile (business block, email signals, missing_info)
                          + dossier (the whole JSON, for anything the columns don't cover)
  fact                    this business's non-user rows are replaced by the dossier's facts; user answers
                          (source_kind 'user', e.g. saved by the form filler) are kept, duplicates skipped
  incentive               inserted only if missing (the legal catalog's richer rows win)
  source / form / uses_form   one form revision per credit form URL, inserted if missing
  eligible_for            one edge per credit for the tax year; stale dossier edges are removed

Read it back with `RETURN fn::business_dossier('<slug>')` or `kb dossier-get <slug>`.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from surrealdb import RecordID

from .config import REPO_ROOT
from .db import without_none
from .ingest import normalize_url

SCHEMA = "moneyfinder.dossier/v1"
ASSESSED_BY = "dossier"
ELIGIBILITY = ("likely", "possible", "needs_info", "ineligible")
KINDS = ("credit", "exemption", "abatement", "refund", "deduction", "grant")
PROGRAM_STATUS = ("active", "expired", "unknown")
ENTITY_TYPES = ("c_corp", "s_corp", "partnership", "llc", "sole_prop", "nonprofit")
BOROUGHS = {
    "manhattan": "Manhattan", "new york county": "Manhattan", "new york": "Manhattan",
    "brooklyn": "Brooklyn", "kings": "Brooklyn", "kings county": "Brooklyn",
    "queens": "Queens", "queens county": "Queens",
    "bronx": "Bronx", "the bronx": "Bronx", "bronx county": "Bronx",
    "staten island": "Staten Island", "richmond": "Staten Island", "richmond county": "Staten Island",
}  # fmt: skip
DOSSIER_GLOBS = ("research/*/data/**/dossier.json",)


# ─── Finding and reading dossiers ────────────────────────────────────────────


def slugify(domain: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", domain.lower().removeprefix("www.")).strip("-")


def find_dossiers(root: Path = REPO_ROOT) -> list[Path]:
    found = {p.resolve() for pattern in DOSSIER_GLOBS for p in root.glob(pattern)}
    return sorted(found, key=lambda p: p.stat().st_mtime, reverse=True)


def resolve_dossier(arg: str, root: Path = REPO_ROOT) -> Path:
    """A path to dossier.json, or a slug/domain whose dossier lives under research/*/data/."""
    path = Path(arg).expanduser()
    if path.is_dir():
        path = path / "dossier.json"
    if path.is_file():
        return path
    wanted = {arg.lower(), slugify(arg)}
    for candidate in find_dossiers(root):
        if candidate.parent.name.lower() in wanted or slugify(candidate.parent.name) in wanted:
            return candidate
        try:
            d = json.loads(candidate.read_text())
        except (OSError, ValueError):
            continue
        if {str(d.get("slug", "")).lower(), str(d.get("domain", "")).lower()} & wanted:
            return candidate
    raise FileNotFoundError(f"no dossier.json for {arg!r} (looked under {root}/research/*/data/)")


def load_dossier(path: Path) -> dict[str, Any]:
    d = json.loads(Path(path).read_text())
    if not isinstance(d, dict):
        raise ValueError(f"{path}: not a JSON object")
    if d.get("schema") not in (None, SCHEMA):
        raise ValueError(f"{path}: schema {d.get('schema')!r}, expected {SCHEMA!r}")
    if not (d.get("slug") or d.get("domain")):
        raise ValueError(f"{path}: needs slug or domain")
    return d


def dossier_slug(d: dict[str, Any]) -> str:
    return str(d.get("slug") or slugify(d["domain"]))


# ─── Normalizing loose research values into the kb's typed columns ──────────


def entity_type(raw: Any) -> str | None:
    if str(raw or "").strip().lower() in ENTITY_TYPES:
        return str(raw).strip().lower()
    s = re.sub(r"[^a-z0-9]+", " ", str(raw or "").lower()).strip()
    if not s:
        return None
    rules = (
        (("not for profit", "nonprofit", "non profit", "501"), "nonprofit"),
        (("s corp", "s corporation", "s_corp"), "s_corp"),
        (("partnership", "llp", "lp"), "partnership"),
        (("llc", "limited liability company", "pllc"), "llc"),
        (("sole", "proprietor"), "sole_prop"),
        (("c corp", "corporation", "inc", "corp", "business corporation"), "c_corp"),
    )
    words = f" {s} "
    for needles, value in rules:
        if any(f" {n} " in words for n in needles):
            return value
    return None


def borough(raw: Any) -> str | None:
    return BOROUGHS.get(re.sub(r"\s+", " ", str(raw or "")).strip().lower())


def as_int(raw: Any) -> int | None:
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float) and raw.is_integer():
        return int(raw)
    s = str(raw or "").replace(",", "").strip()
    return int(s) if s.isdigit() else None


def naics_list(raw: Any) -> list[str]:
    items = raw if isinstance(raw, list) else [raw] if raw else []
    out = []
    for item in items:
        code = item.get("code") if isinstance(item, dict) else item
        code = str(code or "").strip()
        if code and code not in out:
            out.append(code)
    return out


def as_text(value: Any) -> str:
    return value if isinstance(value, str) else json.dumps(value, default=str, sort_keys=True)


def as_datetime(raw: Any) -> datetime | None:
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def as_confidence(raw: Any) -> float | None:
    try:
        x = float(raw)
    except (TypeError, ValueError):
        return None
    return x if 0 <= x <= 1 else None


def jurisdiction(raw: Any) -> str:
    s = str(raw or "").strip().lower()
    if s in ("nyc", "new york city") or s.startswith("nyc") or "city of new york" in s:
        return "NYC"
    if s in ("federal", "us", "usa", "irs", "united states") or "federal" in s:
        return "federal"
    return "NYS"


def default_tax_year(today: date | None = None) -> int:
    return (today or date.today()).year - 1


# ─── Building the push ───────────────────────────────────────────────────────

PUSH_SQL = """
BEGIN TRANSACTION;
UPSERT $b MERGE $business RETURN NONE;
UPDATE $b SET profile = $profile, dossier = $dossier, dossier_at = $at RETURN NONE;
DELETE fact WHERE business = $b AND source_kind != 'user' RETURN NONE;
-- User answers survive the DELETE; skip any dossier fact already stored (INSERT IGNORE does not
-- reliably skip unique-index clashes on every engine version).
FOR $f IN $facts {
    IF array::len((SELECT VALUE id FROM fact WHERE business = $b AND key = $f.key AND value = $f.value AND source = $f.source)) = 0 {
        CREATE fact CONTENT $f RETURN NONE;
    };
};
IF array::len($incentives) > 0 { INSERT IGNORE INTO incentive $incentives RETURN NONE; };
IF array::len($sources) > 0 { INSERT IGNORE INTO source $sources RETURN NONE; };
IF array::len($forms) > 0 { INSERT IGNORE INTO form $forms RETURN NONE; };
IF array::len($uses) > 0 {
    INSERT RELATION INTO uses_form $uses ON DUPLICATE KEY UPDATE role = $input.role RETURN NONE;
};
DELETE eligible_for WHERE in = $b AND tax_year = $year AND assessed_by = $by AND out NOTINSIDE $credit_ids RETURN NONE;
IF array::len($edges) > 0 {
    INSERT RELATION INTO eligible_for $edges ON DUPLICATE KEY UPDATE
        status = $input.status, rank = $input.rank, confidence = $input.confidence, reasons = $input.reasons,
        missing_info = $input.missing_info, assessed_by = $input.assessed_by
    RETURN NONE;
};
COMMIT TRANSACTION;
"""


def build_push(d: dict[str, Any], tax_year: int | None = None, now: datetime | None = None) -> dict[str, Any]:
    """Query parameters for PUSH_SQL. Pure: no I/O, so it is unit-tested directly."""
    slug = dossier_slug(d)
    year = tax_year or default_tax_year()
    now = now or datetime.now(UTC)
    b = RecordID("business", slug)
    biz = d.get("business") or {}
    email = d.get("email") or {}
    missing = [str(m) for m in d.get("missing_info") or []]

    business = without_none(
        {
            "name": biz.get("name") or biz.get("legal_name") or biz.get("dba") or d.get("domain") or slug,
            "legal_name": biz.get("legal_name") or None,
            "domain": d.get("domain"),
            "website": biz.get("website") or (f"https://{d['domain']}" if d.get("domain") else None),
            "naics": naics_list(biz.get("naics")),
            "entity_type": entity_type(biz.get("entity_type")),
            "county": biz.get("county") or None,
            "nyc_borough": borough(biz.get("nyc_borough")),
            "employees": as_int(biz.get("employees")),
        }
    )
    profile = {
        **biz,
        "domain": d.get("domain"),
        "missing_info": missing,
        "email_signals": email.get("signals") or [],
        "email_categories": email.get("categories") or {},
        "dossier_generated_at": d.get("generated_at"),
    }

    facts, seen = [], set()
    for f in d.get("facts") or []:
        if not isinstance(f, dict) or not f.get("key") or f.get("value") in (None, "", [], {}):
            continue
        row = without_none(
            {
                "business": b,
                "key": str(f["key"]),
                "value": as_text(f["value"]),
                "source": str(f.get("source") or f.get("source_kind") or "dossier"),
                "source_kind": f.get("source_kind") or None,
                "confidence": as_confidence(f.get("confidence")),
                "captured_at": as_datetime(f.get("captured_at")) or as_datetime(d.get("generated_at")),
            }
        )
        ident = (row["key"], row["value"], row["source"])
        if ident not in seen:
            seen.add(ident)
            facts.append(row)

    incentives, sources, forms, uses, edges, credit_ids = [], {}, {}, {}, [], []
    for c in d.get("credits") or []:
        if not isinstance(c, dict) or not c.get("id"):
            continue
        inc = RecordID("incentive", str(c["id"]))
        if inc in credit_ids:
            continue
        credit_ids.append(inc)
        incentives.append(
            without_none(
                {
                    "id": inc,
                    "name": str(c.get("name") or c["id"]),
                    "kind": c.get("kind") if c.get("kind") in KINDS else "credit",
                    "jurisdiction": jurisdiction(c.get("jurisdiction")),
                    "agency": c.get("agency") or None,
                    "summary": c.get("eligibility") or c.get("amount") or None,
                    "status": c.get("program_status") if c.get("program_status") in PROGRAM_STATUS
                    else c.get("status") if c.get("status") in PROGRAM_STATUS else None,
                    "requires_preapproval": c.get("requires_preapproval")
                    if isinstance(c.get("requires_preapproval"), bool) else None,
                }
            )
        )
        why = c.get("why") or []
        reasons = [str(w) for w in (why if isinstance(why, list) else [why])]
        status = next(
            (c[k] for k in ("eligibility", "match_status", "status") if c.get(k) in ELIGIBILITY),
            "likely" if c.get("tier") == "niche" else "possible",
        )
        edges.append(
            without_none(
                {
                    "in": b,
                    "out": inc,
                    "tax_year": year,
                    "status": status,
                    "rank": c.get("rank") if isinstance(c.get("rank"), int) else None,
                    "confidence": as_confidence(c.get("confidence")),
                    "reasons": reasons,
                    "missing_info": [str(m) for m in c.get("missing_info") or []],
                    "assessed_by": ASSESSED_BY,
                }
            )
        )
        for form in c.get("forms") or []:
            url = form.get("url") if isinstance(form, dict) else None
            if not url:
                continue
            url = normalize_url(url)
            code = str(form.get("code") or form.get("label") or Path(urlsplit(url).path).stem or url).strip()
            fid = RecordID("form", [code, year])
            src = RecordID("source", url)
            sources.setdefault(url, {"id": src, "url": url, "domain": urlsplit(url).netloc, "authority": "form"})
            forms.setdefault(
                (code, year),
                without_none({"id": fid, "code": code, "tax_year": year, "title": form.get("label") or None,
                              "agency": c.get("agency") or None, "pdf": src}),
            )
            uses.setdefault((str(c["id"]), code), {"in": inc, "out": fid, "role": "claim"})

    return {
        "b": b,
        "business": business,
        "profile": profile,
        "dossier": d,
        "at": now,
        "facts": facts,
        "incentives": incentives,
        "sources": list(sources.values()),
        "forms": list(forms.values()),
        "uses": list(uses.values()),
        "edges": edges,
        "credit_ids": credit_ids,
        "year": year,
        "by": ASSESSED_BY,
    }


def push_summary(params: dict[str, Any]) -> dict[str, Any]:
    return {
        "business": f"business:{params['b'].id}",
        "tax_year": params["year"],
        "facts": len(params["facts"]),
        "credits": len(params["edges"]),
        "forms": len(params["forms"]),
        "missing_info": params["profile"]["missing_info"],
    }


def to_jsonable(value: Any) -> Any:
    """RecordIDs as "table:id", datetimes as ISO strings, everything else as-is."""
    if isinstance(value, RecordID):
        return f"{value.table_name}:{value.id}"
    if isinstance(value, dict):
        return {k: to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]
    if isinstance(value, datetime):
        return value.isoformat()
    return value
