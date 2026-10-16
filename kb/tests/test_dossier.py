import json
import re
from datetime import UTC, datetime
from importlib.resources import files

import pytest
from surrealdb import RecordID

from moneyfinder_kb.config import Settings
from moneyfinder_kb.dossier import (
    build_push,
    borough,
    entity_type,
    load_dossier,
    resolve_dossier,
    slugify,
    to_jsonable,
)

DOSSIER = {
    "schema": "moneyfinder.dossier/v1",
    "slug": "joespizza-com",
    "domain": "joespizza.com",
    "generated_at": "2026-10-16T12:00:00Z",
    "business": {
        "name": "Joe's Pizza",
        "legal_name": "Joe's Pizza LLC",
        "website": "https://joespizza.com",
        "naics": ["722511"],
        "entity_type": "Domestic Limited Liability Company",
        "county": "Kings",
        "nyc_borough": "brooklyn",
        "employees": "14",
        "ein": None,
        "hq_address": "1 Main St, Brooklyn, NY 11201",
    },
    "facts": [
        {"key": "legal_name", "value": "Joe's Pizza LLC", "source": "https://apps.dos.ny.gov/x",
         "source_kind": "registry", "confidence": 0.95, "captured_at": "2026-10-16T11:00:00Z"},
        {"key": "legal_name", "value": "Joe's Pizza LLC", "source": "https://apps.dos.ny.gov/x",
         "source_kind": "registry", "confidence": 0.95},
        {"key": "employees", "value": 14, "source": "apollo", "source_kind": "enrichment", "confidence": 0.6},
        {"key": "ein", "value": None, "source": "web"},
    ],
    "email": {"business_id": "owner-joespizza-com", "signals": ["payroll:gusto"], "categories": {"payroll": 3}},
    "credits": [
        {"id": "nys_restaurant_return_to_work", "name": "Restaurant Return-to-Work Credit", "jurisdiction": "NYS",
         "tier": "niche", "why": ["NAICS 7225 restaurant"], "status": "expired",
         "forms": [{"label": "CT-655", "code": "CT-655", "url": "https://www.tax.ny.gov/pdf/current_forms/ct/ct655.pdf"}]},
        {"id": "federal_wotc", "name": "Work Opportunity Tax Credit", "jurisdiction": "federal", "tier": "broad",
         "why": "hires from target groups", "forms": [{"label": "Form 8850", "url": "https://www.irs.gov/pub/irs-pdf/f8850.pdf"}]},
    ],
    "missing_info": ["ein", "payroll_provider"],
}


def test_normalizers():
    assert entity_type("Domestic Limited Liability Company") == "llc"
    assert entity_type("DOMESTIC BUSINESS CORPORATION") == "c_corp"
    assert entity_type("s_corp") == "s_corp" and entity_type("LLP") == "partnership" and entity_type("?") is None
    assert borough("kings county") == "Brooklyn" and borough("Atlantis") is None
    assert slugify("www.Joes-Pizza.com") == "joes-pizza-com"


def test_build_push():
    p = build_push(DOSSIER, now=datetime(2026, 10, 16, tzinfo=UTC))
    assert p["b"] == RecordID("business", "joespizza-com")
    assert p["year"] == datetime.now().year - 1
    assert p["business"] == {
        "name": "Joe's Pizza", "legal_name": "Joe's Pizza LLC", "domain": "joespizza.com", "website": "https://joespizza.com", "naics": ["722511"],
        "entity_type": "llc", "county": "Kings", "nyc_borough": "Brooklyn", "employees": 14,
    }
    assert p["profile"]["missing_info"] == ["ein", "payroll_provider"]
    assert p["profile"]["email_signals"] == ["payroll:gusto"] and p["profile"]["legal_name"] == "Joe's Pizza LLC"
    assert [(f["key"], f["value"]) for f in p["facts"]] == [("legal_name", "Joe's Pizza LLC"), ("employees", "14")]
    assert p["facts"][0]["captured_at"] == datetime(2026, 10, 16, 11, tzinfo=UTC)
    assert [e["status"] for e in p["edges"]] == ["likely", "possible"]
    assert p["edges"][1]["reasons"] == ["hires from target groups"]
    assert p["incentives"][0]["status"] == "expired" and p["incentives"][1]["jurisdiction"] == "federal"
    assert [f["code"] for f in p["forms"]] == ["CT-655", "Form 8850"]
    assert p["forms"][0]["pdf"] == RecordID("source", "https://www.tax.ny.gov/pdf/current_forms/ct/ct655.pdf")


def test_resolve_and_load(tmp_path):
    d = tmp_path / "research" / "company" / "data" / "joespizza.com"
    d.mkdir(parents=True)
    (d / "dossier.json").write_text(json.dumps(DOSSIER))
    for arg in ("joespizza.com", "joespizza-com", str(d), str(d / "dossier.json")):
        assert resolve_dossier(arg, root=tmp_path) == d / "dossier.json"
    assert load_dossier(d / "dossier.json")["slug"] == "joespizza-com"
    with pytest.raises(FileNotFoundError):
        resolve_dossier("nope.com", root=tmp_path)


# ─── Round trip through the SDK's in-process engine ──────────────────────────
# The embedded engine bundled with surrealdb==2.0.0 speaks SurrealQL 2.x, while the schema targets 3.x
# (SurrealDB Cloud). Translate the three 3.x-only bits so everything else is exercised as written.


def schema_for_embedded_2x() -> str:
    sql = files("moneyfinder_kb").joinpath("schema.surql").read_text()
    sql = re.sub(r"DEFINE FUNCTION OVERWRITE fn::search_chunks.*?\n};\n", "", sql, flags=re.S)
    return sql.replace(" FULLTEXT ANALYZER", " SEARCH ANALYZER").replace("type::record(", "type::thing(")


@pytest.fixture
def kb(tmp_path):
    from moneyfinder_kb.db import DB
    from moneyfinder_kb.kb import KB

    s = Settings.from_env({"SURREAL_URL": "mem://", "LAKE_URI": str(tmp_path / "lake")})
    db = DB(s)
    try:
        db.run(schema_for_embedded_2x())
    except RuntimeError as e:  # pragma: no cover
        pytest.skip(f"embedded engine unavailable: {e}")
    k = KB(s, db, lake=None, embedder=None)
    yield k
    k.close()


def test_round_trip_is_idempotent(kb):
    kb.upsert_incentive("federal_wotc", name="Work Opportunity Tax Credit (catalog)", kind="credit", jurisdiction="federal")
    for _ in range(2):
        summary = kb.push_dossier(DOSSIER, tax_year=2025)
    assert summary["facts"] == 2 and summary["credits"] == 2

    out = to_jsonable(kb.business_dossier("joespizza-com"))
    assert out["record"]["id"] == "business:joespizza-com" and out["record"]["entity_type"] == "llc"
    assert out["business"]["legal_name"] == "Joe's Pizza LLC" and out["business"]["entity_type"].startswith("Domestic")
    assert out["missing_info"] == ["ein", "payroll_provider"] and out["email_signals"] == ["payroll:gusto"]
    assert sorted(f["key"] for f in out["facts"]) == ["employees", "legal_name"]
    credits = {c["id"]: c for c in out["credits"]}
    assert credits["nys_restaurant_return_to_work"]["status"] == "likely"
    assert credits["nys_restaurant_return_to_work"]["forms"][0]["url"].endswith("ct655.pdf")
    assert credits["federal_wotc"]["name"] == "Work Opportunity Tax Credit (catalog)"  # catalog row not overwritten
    assert kb.db.one("SELECT count() FROM eligible_for GROUP ALL")[0]["count"] == 2
    assert kb.db.one("SELECT VALUE dossier.slug FROM ONLY business:`joespizza-com`") == "joespizza-com"

    # A newer dossier with fewer facts and credits replaces facts and drops stale credit edges.
    smaller = {**DOSSIER, "facts": DOSSIER["facts"][:1], "credits": DOSSIER["credits"][1:]}
    kb.push_dossier(smaller, tax_year=2025)
    out = to_jsonable(kb.business_dossier("joespizza-com"))
    assert [f["key"] for f in out["facts"]] == ["legal_name"]
    assert [c["id"] for c in out["credits"]] == ["federal_wotc"]


def test_unknown_slug(kb):
    assert kb.business_dossier("nobody-com")["business"] is None
