import json
import re
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest

from business_research import company, config, ids, store
from business_research.gmail import auth
from business_research.gmail.parse import EmailMessage
from business_research.web.app import create_app

BASE = "http://localhost:8000"
EMAIL = "owner@joespizza.com"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "TOKEN_DIR", tmp_path / "tokens")
    monkeypatch.setattr(config, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(config, "CLIENT_SECRETS_FILE", tmp_path / "credentials.json")
    return create_app(8000).test_client()


def write_client_secrets():
    config.CLIENT_SECRETS_FILE.write_text(
        json.dumps(
            {
                "web": {
                    "client_id": "test-client",
                    "client_secret": "test-secret",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            }
        )
    )


def connect_fake_business() -> str:
    business_id = ids.from_email(EMAIL)
    config.TOKEN_DIR.mkdir(parents=True, exist_ok=True)
    (config.TOKEN_DIR / f"{business_id}.json").write_text(
        json.dumps(
            {
                "email": EMAIL,
                "connected_at": "2026-10-16T12:00:00+00:00",
                "credentials": {"client_id": "id", "client_secret": "s", "refresh_token": "rt", "token": "at"},
            }
        )
    )
    return business_id


def set_csrf(client, token="test-csrf"):
    with client.session_transaction(base_url=BASE) as session:
        session["csrf"] = token
    return token


def test_rejects_unknown_host(client):
    assert client.get("/", base_url="http://attacker.example:8000").status_code == 400


def test_redirects_loopback_ip_to_localhost(client):
    response = client.get("/", base_url="http://127.0.0.1:8000")
    assert response.status_code == 302
    assert response.location.startswith("http://localhost:8000/")


def test_index_explains_missing_oauth_client(client):
    body = client.get("/", base_url=BASE).text
    assert "No OAuth client" in body
    assert "http://localhost:8000/oauth/callback" in body


def test_login_redirects_to_google_with_pkce(client):
    write_client_secrets()
    response = client.get("/login", base_url=BASE)
    assert response.status_code == 302
    url = urlsplit(response.location)
    params = {k: v[0] for k, v in parse_qs(url.query).items()}
    assert url.netloc == "accounts.google.com"
    assert params["redirect_uri"] == "http://localhost:8000/oauth/callback"
    assert params["scope"] == "https://www.googleapis.com/auth/gmail.readonly"
    assert params["code_challenge_method"] == "S256"
    assert params["access_type"] == "offline"
    assert params["prompt"] == "consent"
    with client.session_transaction(base_url=BASE) as session:
        assert session["oauth"]["state"] == params["state"]


def test_callback_rejects_mismatched_state(client, monkeypatch):
    write_client_secrets()
    monkeypatch.setattr(auth, "finish_login", lambda *a: pytest.fail("code exchanged despite bad state"))
    client.get("/login", base_url=BASE)
    response = client.get("/oauth/callback?state=forged&code=abc", base_url=BASE, follow_redirects=True)
    assert "didn&#39;t start here" in response.text


def test_callback_connects_and_opens_business(client, monkeypatch):
    write_client_secrets()
    calls = []

    def fake_finish_login(redirect_uri, code, code_verifier):
        calls.append((redirect_uri, code, code_verifier))
        return auth.get(connect_fake_business())

    monkeypatch.setattr(auth, "finish_login", fake_finish_login)
    company.set_domain(ids.from_email(EMAIL), "joespizza.com")  # returning business: domain already known
    client.get("/login", base_url=BASE)
    with client.session_transaction(base_url=BASE) as session:
        state, verifier = session["oauth"]["state"], session["oauth"]["code_verifier"]

    response = client.get(f"/oauth/callback?state={state}&code=abc", base_url=BASE)
    assert response.status_code == 302
    assert response.location == "/businesses/owner-joespizza-com"
    assert calls == [("http://localhost:8000/oauth/callback", "abc", verifier)]
    with client.session_transaction(base_url=BASE) as session:
        assert "oauth" not in session  # one-time use


def test_post_without_csrf_is_rejected(client, monkeypatch):
    business_id = connect_fake_business()
    monkeypatch.setattr(auth, "disconnect", lambda *a: pytest.fail("disconnected without CSRF token"))
    set_csrf(client)
    assert client.post(f"/businesses/{business_id}/disconnect", base_url=BASE).status_code == 403
    assert client.post(f"/businesses/{business_id}/disconnect", data={"csrf": "wrong"}, base_url=BASE).status_code == 403


def test_mail_content_is_escaped(client):
    business_id = connect_fake_business()
    store.write_messages(
        store.messages_path(business_id),
        [
            EmailMessage(
                id="m1",
                thread_id="t1",
                date="2026-10-01T00:00:00+00:00",
                sender='"Evil" <x@evil.example>',
                sender_domain="evil.example",
                to=EMAIL,
                subject="<script>alert(1)</script>",
                snippet="",
                body='<img src=x onerror="alert(1)">',
            )
        ],
    )
    response = client.get(f"/businesses/{business_id}", base_url=BASE)
    assert response.status_code == 200
    assert "<script>alert" not in response.text and "<img src=x" not in response.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in response.text
    assert "script-src 'self'" in response.headers["Content-Security-Policy"]


def test_unknown_business_is_404(client):
    assert client.get("/businesses/nobody", base_url=BASE).status_code == 404
    assert client.get("/businesses/Bad..Id", base_url=BASE).status_code == 404


def test_disconnect_revokes_and_deletes_everything(client, monkeypatch):
    business_id = connect_fake_business()
    store.messages_path(business_id).parent.mkdir(parents=True)
    store.messages_path(business_id).write_text("{}\n")
    revoked = []

    class FakeRequest:
        def __call__(self, url, method, body, headers):
            revoked.append(body)
            return SimpleNamespace(status=200)

    monkeypatch.setattr(auth, "Request", FakeRequest)
    token = set_csrf(client)
    response = client.post(f"/businesses/{business_id}/disconnect", data={"csrf": token}, base_url=BASE)

    assert response.status_code == 302
    assert revoked == ["token=rt"]
    assert not (config.TOKEN_DIR / f"{business_id}.json").exists()
    assert not store.messages_path(business_id).parent.exists()


def test_rendered_forms_carry_csrf_token(client):
    business_id = connect_fake_business()
    body = client.get(f"/businesses/{business_id}", base_url=BASE).text
    tokens = set(re.findall(r'name="csrf" value="([^"]+)"', body))
    with client.session_transaction(base_url=BASE) as session:
        assert tokens == {session["csrf"]}
