from pathlib import Path

import pytest

from moneyfinder_kb.config import Settings, is_jwt, load_env

CLOUD = "wss://moneyfinder-abc.aws-use1.surreal.cloud"


def settings(**env: str) -> Settings:
    return Settings.from_env(env)


def test_local_defaults_use_root_signin():
    s = settings()
    assert (s.surreal_url, s.surreal_ns, s.surreal_db) == ("ws://127.0.0.1:8000", "moneyfinder", "kb")
    assert (s.surreal_auth, s.surreal_user, s.surreal_pass) == ("root", "root", "root")


def test_cloud_names_and_database_signin():
    s = settings(
        SURREAL_WS_URL=CLOUD,
        SURREAL_URL="https://ignored.example",
        SURREAL_NAMESPACE="moneyfinder",
        SURREAL_DATABASE="main",
        SURREAL_USER="app",
        SURREAL_PASS="pw",
    )
    assert (s.surreal_url, s.surreal_ns, s.surreal_db, s.surreal_auth) == (CLOUD, "moneyfinder", "main", "auto")
    assert "pw" not in s.describe()


def test_short_names_still_work():
    s = settings(SURREAL_URL="ws://localhost:8000", SURREAL_NS="x", SURREAL_DB="y", SURREAL_USER="u", SURREAL_PASS="p")
    assert (s.surreal_ns, s.surreal_db, s.surreal_auth) == ("x", "y", "root")


def test_token_only_if_jwt():
    assert is_jwt("aaa.bbb.ccc") and not is_jwt("01jabcdefghijklmnopqrstuvw") and not is_jwt("a..c")
    s = settings(SURREAL_WS_URL=CLOUD, SURREAL_TOKEN="aaa.bbb.ccc")
    assert (s.surreal_auth, s.surreal_token) == ("token", "aaa.bbb.ccc")
    with pytest.raises(ValueError, match="SURREAL_USER"):
        settings(SURREAL_WS_URL=CLOUD, SURREAL_TOKEN="01jabcdefghijklmnopqrstuvw")


def test_user_pass_beats_token_and_auth_can_be_forced():
    s = settings(SURREAL_WS_URL=CLOUD, SURREAL_TOKEN="aaa.bbb.ccc", SURREAL_USER="u", SURREAL_PASS="p")
    assert s.surreal_auth == "auto"
    assert settings(SURREAL_WS_URL=CLOUD, SURREAL_USER="u", SURREAL_PASS="p", SURREAL_AUTH="namespace").surreal_auth == "namespace"
    assert settings(SURREAL_URL="mem://").surreal_auth == "none"


def test_env_file_precedence(tmp_path: Path):
    root, kb = tmp_path / "root.env", tmp_path / "kb.env"
    root.write_text("SURREAL_DATABASE=main\nSURREAL_NAMESPACE=moneyfinder\nA=root\n")
    kb.write_text("SURREAL_DATABASE=kb_local\nA=kb\n")
    env = load_env({"A": "exported"}, root_env=root, kb_env=kb)
    assert env == {"A": "exported", "SURREAL_DATABASE": "kb_local", "SURREAL_NAMESPACE": "moneyfinder"}
    assert load_env({}, root_env=root, kb_env=tmp_path / "missing")["SURREAL_DATABASE"] == "main"


def test_kb_env_example_blanks_force_local(tmp_path: Path):
    root, kb = tmp_path / "root.env", tmp_path / "kb.env"
    root.write_text(f"SURREAL_WS_URL={CLOUD}\nSURREAL_NAMESPACE=moneyfinder\nSURREAL_DATABASE=main\nSURREAL_USER=app\nSURREAL_PASS=pw\n")
    kb.write_text("SURREAL_URL=ws://127.0.0.1:8000\nSURREAL_WS_URL=\nSURREAL_USER=root\nSURREAL_PASS=root\nSURREAL_DB=kb\nSURREAL_DATABASE=\n")
    s = Settings.from_env(load_env({}, root_env=root, kb_env=kb))
    assert (s.surreal_url, s.surreal_db, s.surreal_auth, s.surreal_user) == ("ws://127.0.0.1:8000", "kb", "root", "root")


class FakeConn:
    def __init__(self, accept: set[str]):
        self.accept, self.calls = accept, []

    def signin(self, vars):
        level = "database" if "database" in vars else "namespace" if "namespace" in vars else "root"
        self.calls.append(level)
        if level not in self.accept:
            raise RuntimeError("There was a problem with authentication")

    def query_raw(self, sql, params):
        self.calls.append(sql)
        return {"result": [{"status": "OK", "result": None}] * 3}

    def use(self, ns, db):
        self.calls.append(("use", ns, db))


@pytest.mark.parametrize("accept,expected", [({"database"}, "database"), ({"root"}, "root")])
def test_auto_signin_falls_back_to_root_and_creates_ns_db(monkeypatch, accept, expected):
    from moneyfinder_kb import db as dbmod

    conn = FakeConn(accept)
    monkeypatch.setattr(dbmod, "Surreal", lambda url: conn)
    d = dbmod.DB(settings(SURREAL_WS_URL=CLOUD, SURREAL_NAMESPACE="moneyfinder", SURREAL_DATABASE="main",
                          SURREAL_USER="u", SURREAL_PASS="p"))
    assert d.auth == expected
    defines = [c for c in conn.calls if isinstance(c, str) and c.startswith("DEFINE NAMESPACE")]
    assert bool(defines) == (expected == "root")
    assert conn.calls[-1] == ("use", "moneyfinder", "main")
