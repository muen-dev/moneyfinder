"""Push a freshly built dossier.json into SurrealDB (the repo's kb/) without blocking the request.

Runs `uv run --project <repo>/kb kb dossier-push <path>` in a background thread, one push at a time.
On only when SURREAL_URL and credentials (SURREAL_USER + SURREAL_PASS, or SURREAL_TOKEN) are set in the
environment, kb/.env or the repo-root .env; KB_AUTO_PUSH=0 turns it off (the tests do). The kb push keeps
user answers (facts with source_kind 'user'), so re-pushing after a rebuild is safe. Failures are logged
with secret values redacted.
"""

import logging
import os
import shutil
import subprocess
import threading
from pathlib import Path

from . import config

log = logging.getLogger(__name__)

REPO_DIR = config.PROJECT_DIR.parents[1]
KB_DIR = REPO_DIR / "kb"
TIMEOUT = 180
SECRET_KEYS = ("SURREAL_PASS", "SURREAL_PASSWORD", "SURREAL_TOKEN")

_lock = threading.Lock()  # pushes for one business must not interleave


def _dotenv(path: Path) -> dict[str, str]:
    """KEY=VALUE lines of a .env file (enough to tell whether a key is set; values are never logged)."""
    out = {}
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return out
    for line in lines:
        key, sep, value = line.strip().removeprefix("export ").partition("=")
        if sep and key.strip() and not key.lstrip().startswith("#"):
            out[key.strip()] = value.strip().strip("'\"")
    return out


def _env() -> dict[str, str]:
    """Same precedence as kb's config: exported variables, then kb/.env, then the repo-root .env."""
    return {**_dotenv(REPO_DIR / ".env"), **_dotenv(KB_DIR / ".env"), **{k: v for k, v in os.environ.items() if v}}


def enabled() -> bool:
    if os.environ.get("KB_AUTO_PUSH", "1").strip().lower() in ("0", "false", "no", "off"):
        return False
    env = _env()
    has_creds = env.get("SURREAL_TOKEN") or (env.get("SURREAL_USER") and (env.get("SURREAL_PASS") or env.get("SURREAL_PASSWORD")))
    return bool(env.get("SURREAL_URL") and has_creds and KB_DIR.is_dir() and shutil.which("uv"))


def push_in_background(path: Path) -> bool:
    """Start pushing this dossier.json to SurrealDB; False when auto-push is off or unconfigured."""
    if not enabled():
        return False
    threading.Thread(target=push, args=(Path(path),), daemon=True, name="kb-dossier-push").start()
    return True


def push(path: Path) -> bool:
    cmd = ["uv", "run", "--project", str(KB_DIR), "kb", "dossier-push", str(path)]
    with _lock:
        try:
            result = subprocess.run(cmd, cwd=REPO_DIR, capture_output=True, text=True, timeout=TIMEOUT)
        except (OSError, subprocess.TimeoutExpired) as e:
            log.warning("kb dossier-push %s failed: %s", path, type(e).__name__)
            return False
    if result.returncode != 0:
        log.warning("kb dossier-push %s exited %d: %s", path, result.returncode, _redact(result.stderr)[-500:])
        return False
    log.info("kb dossier-push %s: %s", path, _redact(result.stdout).strip()[-300:])
    return True


def _redact(text: str) -> str:
    env = _env()
    for key in SECRET_KEYS:
        if len(env.get(key) or "") >= 4:
            text = text.replace(env[key], "[redacted]")
    return text
