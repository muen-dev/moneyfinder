from company_research import pipeline, store
from company_research.collectors import Context, firmographics
from company_research.providers import ProviderError, Recorder

FULLENRICH = {
    "companies": [{
        "name": "Warby Parker", "domain": "warbyparker.com", "description": "Eyewear.", "year_founded": 2010,
        "headcount": 2789, "headcount_range": "1001-5000", "company_type": "Public Company",
        "locations": {"headquarters": {"line1": "161 Avenue of the Americas", "line2": "New York, NY 10013, US",
                                       "city": "New York", "region": "New York", "country_code": "US"}},
        "social_profiles": {"professional_network": {"url": "https://www.linkedin.com/company/warbyparker"}},
        "specialties": ["optician", "retail"], "industry": {"main_industry": "Retail Apparel and Fashion"},
    }],
}


class Fake:
    def __init__(self, answers):
        self.answers, self.calls, self.recorder = answers, [], Recorder()

    def available(self, provider):
        return True

    def alexandria(self, provider, capability, options):
        self.calls.append((provider, capability, options))
        answer = self.answers[provider]
        if isinstance(answer, Exception):
            raise answer
        return answer

    def close(self):
        pass


def test_fullenrich_maps_firmographics_with_provenance():
    fake = Fake({"fullenrich": FULLENRICH})
    result = firmographics.collect(Context("warbyparker.com", fake))
    best = {f.field: f.value for f in result.facts}
    assert best["employee_count"] == 2789 and best["founded_year"] == 2010
    assert best["hq_address"] == "161 Avenue of the Americas, New York, NY 10013, US"
    assert best["industry"] == "Retail Apparel and Fashion"
    assert best["linkedin_url"] == "https://www.linkedin.com/company/warbyparker"
    assert {f.source.via for f in result.facts} == {"fullenrich via Firecrawl Alexandria"}
    assert [c[0] for c in fake.calls] == ["fullenrich"]  # no paid fallback when fullenrich answers


def test_falls_back_to_apollo_and_rejects_other_domains():
    fake = Fake({"fullenrich": {"companies": [{"domain": "other.com", "headcount": 5}]},
                 "apollo": {"organization": {"estimated_num_employees": 12, "industry": "Finance", "city": "Stamford",
                                             "state": "Connecticut", "founded_year": 2019}}})
    result = firmographics.collect(Context("themaincapital.com", fake))
    best = {f.field: f.value for f in result.facts}
    assert best["employee_count"] == 12 and best["founded_year"] == 2019 and best["hq_address"] == "Stamford, Connecticut"
    assert [c[0] for c in fake.calls] == ["fullenrich", "apollo"]


def test_merge_adds_firmographics_and_keeps_stored_facts(tmp_path):
    old = {"domain": "warbyparker.com", "name": "Warby Parker", "inputs": {"domain": "warbyparker.com"}, "generated_at": "x",
           "fields": {"legal_name": [{"value": "Warby Parker Inc.", "confidence": 0.9, "collectors": ["nys_dos"],
                                      "sources": [{"url": "https://data.ny.gov/x", "via": "socrata", "fetched_at": "t"}]}]},
           "collectors": {"nys_dos": {"status": "ok", "error": None, "duration_s": 1, "facts": 1}}}
    store.write_run(tmp_path, old, [])
    fake = Fake({"fullenrich": FULLENRICH, "apollo": ProviderError("terms not accepted")})
    profile = pipeline.research("warbyparker.com", providers=fake, out_dir=tmp_path, only=["firmographics"], merge=True)
    assert profile["best"]["legal_name"] == "Warby Parker Inc."
    assert profile["fields"]["legal_name"][0]["confidence"] == 0.9  # not inflated by re-merging
    assert profile["best"]["employee_count"] == 2789
    assert set(profile["collectors"]) == {"nys_dos", "firmographics"} and profile["name"] == "Warby Parker"
    assert len(list((tmp_path / "raw").glob("*.json"))) == 0  # fake recorded nothing; raw dir kept
