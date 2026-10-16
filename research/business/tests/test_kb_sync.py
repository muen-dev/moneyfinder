"""Auto-push of built dossiers to SurrealDB (kb_sync), with the subprocess and thread faked."""

import logging
import subprocess

from business_research import company, config, kb_sync
from test_company_flow import research_calls  # noqa: F401
from test_web import BASE, EMAIL, client, connect_fake_business, set_csrf  # noqa: F401

SECRET = "pa$$w0rd!secret"


def configure(monkeypatch, tmp_path, **env):
    (tmp_path / "kb").mkdir(exist_ok=True)
    monkeypatch.setattr(kb_sync, "REPO_DIR", tmp_path)
    monkeypatch.setattr(kb_sync, "KB_DIR", tmp_path / "kb")
    for key in ("SURREAL_URL", "SURREAL_USER", "SURREAL_PASS", "SURREAL_PASSWORD", "SURREAL_TOKEN"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)


def test_enabled_needs_url_credentials_and_no_opt_out(monkeypatch, tmp_path):
    configure(monkeypatch, tmp_path, KB_AUTO_PUSH="1", SURREAL_URL="wss://db.example")
    assert not kb_sync.enabled()  # no credentials
    (tmp_path / ".env").write_text(f"SURREAL_USER=moneyfinder\nSURREAL_PASS='{SECRET}'\n")
    assert kb_sync.enabled()
    monkeypatch.setenv("KB_AUTO_PUSH", "0")
    assert not kb_sync.enabled()


def test_push_runs_kb_cli_and_redacts_failures(monkeypatch, tmp_path, caplog):
    configure(monkeypatch, tmp_path, SURREAL_URL="wss://db.example", SURREAL_USER="u", SURREAL_PASS=SECRET)
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 1, "", f"auth failed for {SECRET}")

    monkeypatch.setattr(kb_sync.subprocess, "run", fake_run)
    with caplog.at_level(logging.WARNING):
        assert not kb_sync.push(tmp_path / "dossier.json")
    assert calls == [["uv", "run", "--project", str(tmp_path / "kb"), "kb", "dossier-push", str(tmp_path / "dossier.json")]]
    assert SECRET not in caplog.text and "[redacted]" in caplog.text


def test_finished_research_builds_and_pushes_the_dossier(client, research_calls, monkeypatch):  # noqa: F811
    pushed = []
    monkeypatch.setattr(kb_sync, "push_in_background", pushed.append)
    business_id = connect_fake_business()
    company.set_domain(business_id, "joespizza.com")
    company.start(business_id, "joespizza.com", EMAIL)
    path = config.DATA_DIR / business_id / "dossier.json"
    assert company.status(business_id)["status"] == "done" and path.is_file()
    assert pushed == [path]
    client.get(f"/businesses/{business_id}/dossier.json", base_url=BASE)
    assert pushed == [path]  # cached and current: no rebuild, no second push
