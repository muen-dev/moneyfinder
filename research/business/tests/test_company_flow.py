"""Company-domain signup step and background research, with research mocked (no network)."""

import pytest

from business_research import company, config, store
from business_research.gmail import auth
from test_web import BASE, EMAIL, client, connect_fake_business, set_csrf, write_client_secrets  # noqa: F401


@pytest.fixture
def research_calls(monkeypatch):
    """Run research synchronously with a fake that writes a profile containing hostile content."""
    calls = []

    def fake_research(domain, *, business_id, contact_email, out_dir):
        calls.append((domain, business_id, contact_email))
        from company_research import store as company_store

        company_store.write_run(out_dir, HOSTILE_PROFILE | {"domain": domain}, [])

    monkeypatch.setattr(company, "research_fn", fake_research)
    monkeypatch.setattr(company, "_spawn", lambda target, *args: target(*args))
    company._active.clear()
    return calls


HOSTILE_PROFILE = {
    "schema_version": 1,
    "generated_at": "2026-10-16T12:00:00+00:00",
    "collectors": {"website": {"status": "ok", "error": None, "duration_s": 1.0, "facts": 2}},
    "fields": {
        "description": [
            {
                "value": "<script>alert(1)</script> Pizza in Brooklyn",
                "confidence": 0.65,
                "sources": [{"url": "https://joespizza.com/about", "via": "firecrawl", "fetched_at": "2026-10-16T12:00:00+00:00"}],
            }
        ],
        "news": [
            {
                "value": {"title": "<img src=x onerror=alert(1)>", "url": "javascript:alert(document.cookie)"},
                "confidence": 0.4,
                "sources": [{"url": "javascript:alert(2)", "via": "tavily", "fetched_at": "2026-10-16T12:00:00+00:00"}],
            }
        ],
    },
}


def login_via_callback(client, monkeypatch):
    write_client_secrets()
    monkeypatch.setattr(auth, "finish_login", lambda *a: auth.get(connect_fake_business()))
    client.get("/login", base_url=BASE)
    with client.session_transaction(base_url=BASE) as session:
        state = session["oauth"]["state"]
    return client.get(f"/oauth/callback?state={state}&code=abc", base_url=BASE)


def test_callback_without_domain_asks_for_it(client, monkeypatch):
    response = login_via_callback(client, monkeypatch)
    assert response.status_code == 302
    assert response.location == "/businesses/owner-joespizza-com/domain"


def test_domain_form_prefills_company_email_domain(client):
    business_id = connect_fake_business()
    body = client.get(f"/businesses/{business_id}/domain", base_url=BASE).text
    assert 'value="joespizza.com"' in body


@pytest.mark.parametrize("email", ["owner@gmail.com", "owner@outlook.com", "x@yahoo.co.uk", "a@icloud.com", "p@proton.me"])
def test_domain_form_does_not_prefill_free_providers(email):
    assert company.suggested_domain(email) == ""


def test_domain_post_requires_csrf(client, research_calls):
    business_id = connect_fake_business()
    set_csrf(client)
    assert client.post(f"/businesses/{business_id}/domain", data={"domain": "joespizza.com"}, base_url=BASE).status_code == 403
    assert client.post(f"/businesses/{business_id}/research", base_url=BASE).status_code == 403
    assert company.get_domain(business_id) is None and research_calls == []


@pytest.mark.parametrize("bad", ["localhost", "127.0.0.1", "http://10.0.0.1/", "joespizza.com:8080", "printer.local", "co.uk", "gmail.com"])
def test_domain_post_rejects_invalid(client, research_calls, bad):
    business_id = connect_fake_business()
    token = set_csrf(client)
    response = client.post(f"/businesses/{business_id}/domain", data={"domain": bad, "csrf": token}, base_url=BASE)
    assert response.status_code == 400
    assert company.get_domain(business_id) is None and research_calls == []


def test_domain_post_saves_and_runs_research(client, research_calls):
    business_id = connect_fake_business()
    token = set_csrf(client)
    response = client.post(
        f"/businesses/{business_id}/domain", data={"domain": "https://WWW.JoesPizza.com/menu", "csrf": token}, base_url=BASE
    )
    assert response.status_code == 302 and response.location == f"/businesses/{business_id}"
    assert company.get_domain(business_id) == "joespizza.com"
    assert research_calls == [("joespizza.com", business_id, EMAIL)]
    assert company.status(business_id)["status"] == "done"
    business_json = config.DATA_DIR / business_id / "business.json"
    assert oct(business_json.stat().st_mode & 0o777) == "0o600"
    assert '"domain"' not in (config.TOKEN_DIR / f"{business_id}.json").read_text()  # kept out of the token file


def test_scraped_content_is_escaped_and_never_a_script_link(client, research_calls):
    business_id = connect_fake_business()
    company.set_domain(business_id, "joespizza.com")
    company.start(business_id, "joespizza.com", EMAIL)
    body = client.get(f"/businesses/{business_id}", base_url=BASE).text
    assert "<script>alert" not in body and "<img src=x" not in body
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in body
    assert "javascript:" not in body.split("<main>")[1].replace("&#34;", "")  # no hostile URL rendered as a link
    assert 'href="https://joespizza.com/about"' in body
    assert "done" in body


def test_running_status_refreshes_and_failure_shows_error(client, monkeypatch):
    business_id = connect_fake_business()
    company.set_domain(business_id, "joespizza.com")
    company._active.add(business_id)
    company._write(config.DATA_DIR / business_id / "research.json", {"status": "running", "domain": "joespizza.com"})
    body = client.get(f"/businesses/{business_id}", base_url=BASE).text
    assert '<meta http-equiv="refresh"' in body and "running" in body

    company._active.clear()
    company._write(
        config.DATA_DIR / business_id / "research.json",
        {"status": "failed", "domain": "joespizza.com", "error": "firecrawl: HTTP 402 <b>quota</b>"},
    )
    body = client.get(f"/businesses/{business_id}", base_url=BASE).text
    assert '<meta http-equiv="refresh"' not in body
    assert "Research failed: firecrawl: HTTP 402 &lt;b&gt;quota&lt;/b&gt;" in body


def test_disconnect_deletes_domain_and_research(client, research_calls, monkeypatch):
    business_id = connect_fake_business()
    company.set_domain(business_id, "joespizza.com")
    company.start(business_id, "joespizza.com", EMAIL)
    assert company.profile(business_id) is not None
    monkeypatch.setattr(auth, "disconnect", lambda business_id: (config.TOKEN_DIR / f"{business_id}.json").unlink() or True)
    token = set_csrf(client)
    client.post(f"/businesses/{business_id}/disconnect", data={"csrf": token}, base_url=BASE)
    assert not (config.DATA_DIR / business_id).exists()
    assert company.get_domain(business_id) is None and company.profile(business_id) is None
    assert store.read_messages(business_id) == []


def test_domain_form_stores_company_name_and_business_page_shows_dossier(client, research_calls):
    business_id = connect_fake_business()
    form = client.get(f"/businesses/{business_id}/domain", base_url=BASE)
    assert b'name="name"' in form.data
    token = set_csrf(client)
    client.post(f"/businesses/{business_id}/domain", data={"domain": "joespizza.com", "name": "  Joe's   Pizza ", "csrf": token}, base_url=BASE)
    assert company.info(business_id)["name"] == "Joe's Pizza"
    page = client.get(f"/businesses/{business_id}", base_url=BASE)
    assert b"Form-ready dossier" in page.data
    data = client.get(f"/businesses/{business_id}/dossier.json", base_url=BASE).get_json()
    assert data["business"]["name"] == "Joe's Pizza" and data["business"]["contact_email"] == EMAIL
    assert any(f["key"] == "name" and f["source_kind"] == "user" for f in data["facts"])
