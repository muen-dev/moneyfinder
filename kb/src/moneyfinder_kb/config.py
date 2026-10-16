"""Settings, read from the environment.

Load order (first wins per key): exported environment variables, then kb/.env, then the repo-root .env.
So the shared root .env (SurrealDB Cloud) works out of the box, kb/.env can point at a local
database, and anything exported in the shell beats both.

SurrealDB variables (either spelling works; the first one listed wins):
  SURREAL_WS_URL | SURREAL_URL        default ws://127.0.0.1:8000
  SURREAL_NAMESPACE | SURREAL_NS      default moneyfinder
  SURREAL_DATABASE | SURREAL_DB       default kb
  SURREAL_USER / SURREAL_PASS         default root/root, local only
  SURREAL_TOKEN                       used only if it is a JWT (three dot-separated parts)
  SURREAL_AUTH                        force auto | root | namespace | database | token | none

Auth when SURREAL_AUTH is unset: user+pass on a local URL -> root signin; user+pass on a remote
URL (SurrealDB Cloud) -> "auto": database-level signin, falling back to root-level (system user);
else a JWT token -> authenticate; else local -> root/root.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import dotenv_values

KB_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = KB_ROOT.parent

DEFAULT_URL = "ws://127.0.0.1:8000"
AUTH_MODES = ("auto", "root", "namespace", "database", "token", "none")


def load_env(
    environ: dict[str, str] | None = None,
    root_env: Path = REPO_ROOT / ".env",
    kb_env: Path = KB_ROOT / ".env",
) -> dict[str, str]:
    """Fill `environ` (default os.environ) from kb/.env, then the root .env, never overriding a set key."""
    environ = os.environ if environ is None else environ
    for path in (kb_env, root_env):
        if path.is_file():
            for key, value in dotenv_values(path).items():
                if value is not None and key not in environ:
                    environ[key] = value
    return environ


def is_jwt(token: str | None) -> bool:
    parts = (token or "").strip().split(".")
    return len(parts) == 3 and all(parts)


def is_local(url: str) -> bool:
    if url.startswith(("mem://", "memory", "file://", "surrealkv")):
        return True
    return (urlsplit(url).hostname or "") in {"127.0.0.1", "localhost", "0.0.0.0", "::1", "surrealdb"}


def _first(env: Mapping[str, str], *keys: str, default: str | None = None) -> str | None:
    for key in keys:
        if env.get(key):
            return env[key].strip()
    return default


def resolve_auth(url: str, user: str | None, password: str | None, token: str | None, forced: str | None) -> str:
    if forced:
        if forced not in AUTH_MODES:
            raise ValueError(f"SURREAL_AUTH must be one of {AUTH_MODES}, got {forced!r}")
        return forced
    if url.startswith(("mem://", "memory")):
        return "none"
    if user and password:
        return "root" if is_local(url) else "auto"
    if is_jwt(token):
        return "token"
    if is_local(url):
        return "root"
    raise ValueError(
        f"No usable SurrealDB credentials for {urlsplit(url).hostname}: set SURREAL_USER and SURREAL_PASS "
        "(database-level user) or a JWT in SURREAL_TOKEN in the repo-root .env"
    )


@dataclass(frozen=True)
class Settings:
    surreal_url: str
    surreal_user: str | None
    surreal_pass: str | None
    surreal_ns: str
    surreal_db: str
    lake_uri: str
    aws_region: str
    embed_model: str | None
    embed_dim: int
    firecrawl_api_key: str | None
    surreal_token: str | None = None
    surreal_auth: str = "root"

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None, load: bool = True) -> Settings:
        env = load_env() if environ is None and load else (environ if environ is not None else os.environ)
        url = _first(env, "SURREAL_WS_URL", "SURREAL_URL", default=DEFAULT_URL)
        user = _first(env, "SURREAL_USER")
        password = _first(env, "SURREAL_PASS", "SURREAL_PASSWORD")
        token = _first(env, "SURREAL_TOKEN")
        if not user and not password and is_local(url):
            user, password = "root", "root"
        auth = resolve_auth(url, user, password, token, _first(env, "SURREAL_AUTH"))
        return cls(
            surreal_url=url,
            surreal_user=user,
            surreal_pass=password,
            surreal_ns=_first(env, "SURREAL_NAMESPACE", "SURREAL_NS", default="moneyfinder"),
            surreal_db=_first(env, "SURREAL_DATABASE", "SURREAL_DB", default="kb"),
            lake_uri=_first(env, "LAKE_URI", default=str(KB_ROOT / "lake")),
            aws_region=_first(env, "AWS_REGION", default="us-east-1"),
            embed_model=_first(env, "EMBED_MODEL"),
            embed_dim=int(_first(env, "EMBED_DIM", default="1024")),
            firecrawl_api_key=_first(env, "FIRECRAWL_API_KEY"),
            surreal_token=token if is_jwt(token) else None,
            surreal_auth=auth,
        )

    def describe(self) -> str:
        """Where and how we connect, without secrets."""
        host = urlsplit(self.surreal_url).hostname or self.surreal_url
        who = f" as {self.surreal_user}" if self.surreal_user and self.surreal_auth not in ("token", "none") else ""
        return f"{host} ns={self.surreal_ns} db={self.surreal_db} auth={self.surreal_auth}{who}"
