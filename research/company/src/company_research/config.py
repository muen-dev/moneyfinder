"""Paths, API keys and limits, overridable through environment variables.

Keys come from the environment, falling back to research/company/.env.local (git-ignored).
"""

import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]  # research/company
ENV_FILE = Path(os.environ.get("COMPANY_ENV_FILE", PROJECT_DIR / ".env.local"))
ROOT_ENV_FILE = PROJECT_DIR.parents[1] / ".env"
DATA_DIR = Path(os.environ.get("COMPANY_DATA_DIR", PROJECT_DIR / "data"))

KEY_NAMES = ("TAVILY_API_KEY", "FIRECRAWL_API_KEY", "NIMBLE_API_KEY")

# Per-request and per-collector time limits (seconds).
HTTP_TIMEOUT = float(os.environ.get("COMPANY_HTTP_TIMEOUT", "60"))
COLLECTOR_TIMEOUT = float(os.environ.get("COMPANY_COLLECTOR_TIMEOUT", "150"))

# Cap on scraped text kept per page and sent to the optional LLM step.
MAX_PAGE_CHARS = 20_000
MAX_LLM_INPUT_CHARS = 12_000

# Converse takes an inference-profile id. Claude models newer than Opus 4.6 have no ARN-versioned
# id and are not reachable through Converse, so the default is the newest one that is.
DEFAULT_BEDROCK_MODEL_ID = "global.anthropic.claude-opus-4-6-v1"


def load_env_file(path: Path | None = None) -> None:
    """Load KEY=VALUE lines into os.environ without overriding variables that are already set."""
    paths = [path] if path else [ENV_FILE, ROOT_ENV_FILE]
    for env_path in paths:
        if not env_path.is_file():
            continue
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key, value = key.strip().removeprefix("export ").strip(), value.strip().strip("'\"")
            if key and value:
                os.environ.setdefault(key, value)


def api_key(name: str) -> str | None:
    load_env_file()
    return os.environ.get(name) or None


def setting(name: str, default: str = "") -> str:
    load_env_file()
    return os.environ.get(name) or default


def keys_present() -> dict[str, bool]:
    """Which provider keys are configured (names only; values are never returned)."""
    return {name: api_key(name) is not None for name in KEY_NAMES}
