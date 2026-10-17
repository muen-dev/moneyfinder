"""Matched credits on the profile pages, stored company profiles, and the mounted Track path UI."""

import json

import pytest
from company_research import config as company_config
from legal_research import config as legal_config

from business_research import company
from business_research.web import app as web_app
from test_web import BASE, client, connect_fake_business  # noqa: F401  (fixture)

CATALOG = {
    "niches": [{"id": "small_retail", "label": "Small shops and stores", "naics": ["45"], "profile_keywords": ["retail"]},
               {"id": "employee_benefits", "label": "Benefits", "naics": [], "profile_keywords": ["benefits"]}],
    "programs": [
        {"id": "nys_commercial_security", "name": "Commercial security credit", "jurisdiction": "NYS", "status": "active",
         "url": "https://www.tax.ny.gov/pit/credits/commercial_security.htm", "niches": ["small_retail"],
         "claims": [{"taxpayers": 7, "amount": 21000, "latest_year": 2023}],
         "facts": {"amount": "$3,000 per location", "forms": [
             {"code": "CT-663", "pdf": "https://www.tax.ny.gov/pdf/current_forms/ct/ct663.pdf"},
             {"code": "IT-663", "pdf": "javascript:alert(1)"}]}},
        {"id": "fed_small_employer_health", "name": "Small business health care tax credit", "jurisdiction": "federal",
         "status": "unknown", "url": "https://www.irs.gov/forms-pubs/about-form-8941", "niches": ["employee_benefits"],
         "facts": {"forms": [{"code": "8941", "pdf": "https://www.irs.gov/pub/irs-pdf/f8941.pdf"}]}},
    ],
}


def profile(domain="glassesco.com"):
    claim = lambda v: {"value": v, "confidence": 0.9, "sources": [{"url": "https://glassesco.com/", "via": "t", "fetched_at": ""}]}  # noqa: E731
    return {"schema_version": 1, "domain": domain, "name": "Glasses Co", "generated_at": "2026-10-16T12:00:00",
            "best": {"industry": "Retail (Eyewear)"}, "collectors": {},
            "fields": {"naics": [claim({"code": "456130", "title": "Optical Goods Retailers"})],
                       "industry": [claim("Retail (Eyewear)")]}}


@pytest.fixture
def data(tmp_path, monkeypatch):
    monkeypatch.setattr(company_config, "DATA_DIR", tmp_path / "company")
    monkeypatch.setattr(legal_config, "DATA_DIR", tmp_path / "legal")
    web_app._catalog_cache.clear()
    (tmp_path / "legal").mkdir()
    (tmp_path / "legal" / "catalog.json").write_text(json.dumps(CATALOG))
    (tmp_path / "company" / "glassesco.com").mkdir(parents=True)
    (tmp_path / "company" / "glassesco.com" / "profile.json").write_text(json.dumps(profile()))
    return tmp_path


def test_index_lists_stored_company_profiles(client, data):
    body = client.get("/", base_url=BASE).get_data(as_text=True)
    assert "/companies/glassesco.com" in body and "Glasses Co" in body


def test_company_page_shows_matched_credits_with_official_pdf_links(client, data):
    r = client.get("/companies/glassesco.com", base_url=BASE)
    body = r.get_data(as_text=True)
    assert r.status_code == 200
    assert "Credits you may qualify for" in body and "Commercial security credit" in body
    assert "NAICS 456130 is in Small shops and stores" in body
    assert "<strong>7</strong> NY taxpayers claimed it in 2023" in body
    assert 'href="https://www.tax.ny.gov/pdf/current_forms/ct/ct663.pdf"' in body
    assert "javascript:" not in body  # only http(s) form links render
    assert "Credits most employers can claim" in body and "f8941.pdf" in body
    assert "Re-run" not in body  # no Gmail connection, so no research actions


@pytest.mark.parametrize("domain", ["missing.example", "not a domain", "..%2f..%2fetc"])
def test_company_page_404s_for_unknown_or_invalid_domains(client, data, domain):
    assert client.get(f"/companies/{domain}", base_url=BASE).status_code == 404


def test_business_page_shows_credits_from_its_research(client, data):
    business_id = connect_fake_business()
    company.set_domain(business_id, "glassesco.com")
    out = company.research_dir(business_id)
    out.mkdir(parents=True)
    (out / "profile.json").write_text(json.dumps(profile()))
    body = client.get(f"/businesses/{business_id}", base_url=BASE).get_data(as_text=True)
    assert "Commercial security credit" in body and "ct663.pdf" in body


def test_business_page_without_catalog_still_renders(client, data):
    (data / "legal" / "catalog.json").unlink()
    web_app._catalog_cache.clear()
    r = client.get("/companies/glassesco.com", base_url=BASE)
    assert r.status_code == 200 and "No industry-specific credits matched" in r.get_data(as_text=True)


@pytest.mark.parametrize(
    "path, marker",
    [
        ("/track/", "MoneyFinder Track"),
        ("/track/", "Research my business"),
        ("/mock-portal/", "Mock NY Unclaimed Funds"),
    ],
)
def test_track_path_is_mounted_with_its_own_csp(client, path, marker):
    r = client.get(path, base_url=BASE)
    assert r.status_code == 200 and marker in r.get_data(as_text=True)
    assert "'unsafe-inline'" in r.headers["Content-Security-Policy"]
    if path.startswith("/track"):
        assert "connect-src 'self'" in r.headers["Content-Security-Policy"]
    strict = client.get("/", base_url=BASE).headers["Content-Security-Policy"]
    assert "unsafe-inline" not in strict and "script-src 'self'" in strict
    home = client.get("/", base_url=BASE).get_data(as_text=True)
    assert 'href="/track/"' in home and ">Track<" in home


def test_unclaimed_redirects_to_track(client):
    r = client.get("/unclaimed/", base_url=BASE)
    assert r.status_code in (301, 302)
    assert r.headers["Location"].endswith("/track/")


def test_track_api_on_flask(client):
    health = client.get("/api/health", base_url=BASE)
    assert health.status_code == 200
    assert health.get_json().get("surface") == "track"
    tracker = client.get("/api/tracker", base_url=BASE)
    assert tracker.status_code == 200
    assert isinstance(tracker.get_json(), dict)


def test_track_api_post_skips_csrf(client):
    r = client.post("/api/demo/reset", json={}, base_url=BASE)
    assert r.status_code == 200
    assert r.get_json().get("ok") is True
