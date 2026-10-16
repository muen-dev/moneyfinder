"""Profile -> program matching on a tiny in-memory catalog (no network, no data files)."""

from legal_research.match import match_programs

CATALOG = {
    "niches": [
        {"id": "small_retail", "label": "Small shops and stores", "naics": ["44", "45"], "profile_keywords": ["retail", "store"]},
        {"id": "life_sciences", "label": "Biotech", "naics": ["3254"], "profile_keywords": ["biotech"]},
        {"id": "research_development", "label": "R&D", "naics": ["5417"], "profile_keywords": ["R&D", "research"]},
        {"id": "restaurants_hospitality", "label": "Restaurants", "naics": ["722"], "profile_keywords": ["bar", "restaurant"]},
        {"id": "employee_benefits", "label": "Small-employer benefits", "naics": [], "profile_keywords": ["benefits"]},
        {"id": "legacy_zones", "label": "Legacy zones", "naics": [], "profile_keywords": []},
    ],
    "programs": [
        {"id": "nys_commercial_security", "name": "Commercial security", "jurisdiction": "NYS", "status": "active",
         "niches": ["small_retail"], "claims": [{"taxpayers": 12, "amount": 36000, "latest_year": 2023}],
         "facts": {"amount": "$3,000 per location", "forms": [
             {"code": "CT-663", "pdf": "https://www.tax.ny.gov/pdf/current_forms/ct/ct663.pdf"},
             {"code": "IT-663", "pdf": None, "page": "https://www.tax.ny.gov/x.htm"}]}},
        {"id": "nys_niche_zero", "name": "Retail credit nobody claims", "jurisdiction": "NYS", "status": "active",
         "niches": ["small_retail"], "claims": [{"taxpayers": 0, "amount": 0, "latest_year": 2023}], "facts": {}},
        {"id": "nys_life_rd", "name": "Life sciences R&D", "jurisdiction": "NYS", "status": "active",
         "niches": ["life_sciences", "research_development"], "facts": {}},
        {"id": "fed_research", "name": "R&D credit", "jurisdiction": "federal", "status": "unknown",
         "niches": ["research_development"], "facts": {"forms": [{"code": "6765", "pdf": "https://www.irs.gov/pub/irs-pdf/f6765.pdf"}]}},
        {"id": "fed_fica_tip", "name": "FICA tip credit", "jurisdiction": "federal", "status": "unknown",
         "niches": ["restaurants_hospitality"], "facts": {}},
        {"id": "fed_small_employer_health", "name": "Health care credit", "jurisdiction": "federal", "status": "unknown",
         "niches": ["employee_benefits"], "facts": {"forms": [{"code": "8941", "pdf": "https://www.irs.gov/pub/irs-pdf/f8941.pdf"}]}},
        {"id": "nys_zone", "name": "Zone credit", "jurisdiction": "NYS", "status": "active", "niches": ["small_retail", "legacy_zones"], "facts": {}},
        {"id": "untagged", "name": "No niche", "jurisdiction": "NYS", "status": "active", "niches": [], "facts": {}},
    ],
}


def claim(value, url="https://example.com/src"):
    return {"value": value, "confidence": 0.9, "sources": [{"url": url, "via": "test", "fetched_at": ""}]}


PROFILE = {
    "domain": "glasses.example",
    "fields": {
        "naics": [claim({"code": "456130", "title": "Optical Goods Retailers"})],
        "description": [claim("We design eyeglasses and offer vision benefits at our barbershop-free stores.")],
        "rd_tech_signals": [claim({"title": "Virtual try-on app", "snippet": "biotech noise"})],
    },
}


def by_id(matches):
    return {m["id"]: m for m in matches}


def test_niche_first_fewest_claimants_first_with_why_and_pdf_forms():
    matches = match_programs(PROFILE, CATALOG)
    ids = [m["id"] for m in matches]
    assert ids[:2] == ["nys_niche_zero", "nys_commercial_security"]  # niche credits, fewest claimants first
    security = by_id(matches)["nys_commercial_security"]
    assert security["tier"] == "niche" and security["claimants"] == 12
    assert any("NAICS 456130" in line for line in security["why"])
    assert security["forms"] == [{"label": "CT-663 (corporations)", "code": "CT-663",
                                  "url": "https://www.tax.ny.gov/pdf/current_forms/ct/ct663.pdf", "instructions": None}]
    assert security["amount"] == "$3,000 per location"


def test_signals_count_and_industry_credits_need_every_industry():
    matches = by_id(match_programs(PROFILE, CATALOG))
    assert "fed_research" in matches  # R&D signal alone
    assert "nys_life_rd" not in matches  # also needs life sciences
    assert "fed_fica_tip" not in matches  # "bar" must be a whole word, not "barbershop"


def test_broad_credits_ranked_last_and_closed_or_untagged_skipped():
    matches = match_programs(PROFILE, CATALOG)
    health = by_id(matches)["fed_small_employer_health"]
    assert health["tier"] == "broad" and matches[-1]["tier"] == "broad"
    assert health["evidence"] == []  # "vision benefits" in a description is not evidence of employee benefits
    assert not {"nys_zone", "untagged"} & set(by_id(matches))


def test_flat_profile_and_empty_inputs():
    flat = {"industry": "Restaurant", "naics": "722511"}
    assert "fed_fica_tip" in by_id(match_programs(flat, CATALOG))
    assert match_programs({}, CATALOG) == []
    assert match_programs(PROFILE, {"niches": [], "programs": []}) == []
