"""Tests for domain-first profile mapping and imported money data."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.profile_mapper import company_profile_to_search_profile
from src.search.imported import ImportedNYUnclaimedAdapter


def test_company_profile_maps_to_search_profile() -> None:
    result = company_profile_to_search_profile(
        {
            "domain": "example.com",
            "best": {
                "legal_name": "Example Foods LLC",
                "hq_address": "123 Main Street",
                "city": "Brooklyn",
                "state": "NY",
                "zip": "11201",
                "entity_type": "LLC",
                "authorized_representative": {"name": "Maria", "role": "Member"},
            },
            "fields": {},
        },
        consent=True,
    )
    assert result["legal_name"] == "Example Foods LLC"
    assert result["addresses"][0]["zip"] == "11201"
    assert result["authorized_representative"]["name"] == "Maria"


def test_imported_adapter_reads_json(tmp_path: Path) -> None:
    path = tmp_path / "ny.json"
    path.write_text(
        json.dumps(
            [
                {
                    "name": "Example Foods",
                    "property_type": "Uncashed check",
                    "city": "Brooklyn",
                    "zip": "11201",
                    "amount": 412,
                    "source": "test-import",
                }
            ]
        )
    )
    hits = ImportedNYUnclaimedAdapter(path).search(
        {
            "legal_name": "Example Foods LLC",
            "dbas": [],
            "addresses": [{"city": "Brooklyn", "zip": "11201"}],
        }
    )
    assert len(hits) == 1
    assert hits[0].amount_cents == 41200
    assert hits[0].source == "test-import"


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


STORED_PROFILE = {
    "schema_version": 1,
    "domain": "acmebakery.example",
    "generated_at": "2026-10-01T12:00:00+00:00",
    "best": {
        "legal_name": "Acme Bakery LLC",
        "dba": "Acme",
        "hq_address": "12 Court Street, Suite 3, Brooklyn, NY 11201-4321",
        "entity_type": "Domestic Limited Liability Company",
    },
    "fields": {"legal_name": [{"value": "Acme Bakery LLC", "confidence": 0.9, "sources": [], "collectors": ["nys_dos"]}]},
    "collectors": {"nys_dos": {"status": "ok"}},
}


def test_research_domain_returns_stored_profile_and_dossier(tmp_path: Path, monkeypatch) -> None:
    from src import server

    monkeypatch.setattr(server, "COMPANY_DATA_DIR", tmp_path)
    monkeypatch.delenv("COMPANY_RESEARCH_LIVE", raising=False)
    _write(tmp_path / "acmebakery.example" / "profile.json", STORED_PROFILE)
    dossier = {
        "domain": "acmebakery.example",
        "business": {"officer_name": "Ana Ruiz", "officer_title": "Managing Member"},
        "credits": [{"id": "ny-example-credit"}],
        "missing_info": ["ein"],
    }
    _write(tmp_path / "acmebakery.example" / "dossier.json", dossier)

    result = server.research_domain("https://www.AcmeBakery.example/about")

    assert result["research_mode"] == "stored"
    assert "demo_only" not in result
    best = result["best"]
    assert best["legal_name"] == "Acme Bakery LLC"
    assert best["hq_address"] == "12 Court Street, Suite 3"
    assert best["hq_address_full"] == "12 Court Street, Suite 3, Brooklyn, NY 11201-4321"
    assert (best["city"], best["state"], best["zip"]) == ("Brooklyn", "NY", "11201")
    assert best["dbas"] == ["Acme"]
    assert result["dossier"]["credits"] == [{"id": "ny-example-credit"}]
    assert result["dossier"]["missing_info"] == ["ein"]

    mapped = company_profile_to_search_profile(result, consent=True)
    assert mapped["legal_name"] == "Acme Bakery LLC"
    assert mapped["dbas"] == ["Acme"]
    assert mapped["addresses"][0] == {
        "street": "12 Court Street, Suite 3",
        "city": "Brooklyn",
        "state": "NY",
        "zip": "11201",
        "current": True,
        "source": "company_research",
    }
    assert mapped["authorized_representative"]["name"] == "Ana Ruiz"
    assert mapped["research_source"] == "acmebakery.example"


def test_research_domain_stored_profile_without_dossier(tmp_path: Path, monkeypatch) -> None:
    from src import server

    monkeypatch.setattr(server, "COMPANY_DATA_DIR", tmp_path)
    _write(tmp_path / "acmebakery.example" / "profile.json", STORED_PROFILE)

    result = server.research_domain("acmebakery.example")

    assert "dossier" not in result
    assert result["best"]["city"] == "Brooklyn"


def test_research_domain_demo_stub_when_nothing_stored(tmp_path: Path, monkeypatch) -> None:
    from src import server

    monkeypatch.setattr(server, "COMPANY_DATA_DIR", tmp_path)
    monkeypatch.delenv("COMPANY_RESEARCH_LIVE", raising=False)

    result = server.research_domain("unknown-shop.com")

    assert result["demo_only"] is True
    assert result["best"]["legal_name"] == "Unknown Shop"


def test_research_domain_rejects_bad_domains(tmp_path: Path, monkeypatch) -> None:
    import pytest

    from src import server

    monkeypatch.setattr(server, "COMPANY_DATA_DIR", tmp_path)
    for bad in ("", "localhost", "..", "../etc", "a..b"):
        with pytest.raises(ValueError):
            server.research_domain(bad)


def test_research_domain_live_runs_subprocess_then_reads_store(tmp_path: Path, monkeypatch) -> None:
    from src import server

    monkeypatch.setattr(server, "COMPANY_DATA_DIR", tmp_path)
    monkeypatch.setenv("COMPANY_RESEARCH_LIVE", "1")
    calls = []
    writer = (
        "import json, pathlib, sys; out = pathlib.Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True); "
        "(out / 'profile.json').write_text(sys.argv[2])"
    )

    def fake_command(domain: str, out_dir: Path) -> list[str]:
        calls.append((domain, out_dir))
        return [sys.executable, "-c", writer, str(out_dir), json.dumps(STORED_PROFILE)]

    monkeypatch.setattr(server, "_live_research_command", fake_command)

    result = server.research_domain("acmebakery.example")

    assert calls == [("acmebakery.example", tmp_path / "acmebakery.example")]
    assert result["research_mode"] == "live"
    assert result["best"]["zip"] == "11201"


def test_research_domain_live_failure_raises(tmp_path: Path, monkeypatch) -> None:
    import pytest

    from src import server

    monkeypatch.setattr(server, "COMPANY_DATA_DIR", tmp_path)
    monkeypatch.setenv("COMPANY_RESEARCH_LIVE", "1")
    monkeypatch.setattr(
        server,
        "_live_research_command",
        lambda domain, out_dir: [sys.executable, "-c", "import sys; print('error: no keys', file=sys.stderr); sys.exit(1)"],
    )

    with pytest.raises(RuntimeError, match="no keys"):
        server.research_domain("acmebakery.example")


def test_stored_demo_business_maps_cleanly() -> None:
    from src import server

    if not (server.COMPANY_DATA_DIR / "gowanuskettle.example" / "profile.json").exists():
        return
    result = server.research_domain("gowanuskettle.example")
    mapped = company_profile_to_search_profile(result, consent=True)
    assert mapped["legal_name"] == "Gowanus Kettle Brewing Co. LLC"
    assert mapped["addresses"][0]["street"] == "417 Sackett Street"
    assert mapped["addresses"][0]["zip"] == "11231"
    assert "credits" in result["dossier"]
