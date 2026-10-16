"""Paths, API keys, official hosts and limits, overridable through environment variables.

Keys come from the environment, falling back to research/legal/.env.local (git-ignored).
"""

import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]  # research/legal
CATALOG_DIR = Path(os.environ.get("LEGAL_CATALOG_DIR", PROJECT_DIR / "catalog"))
ENV_FILE = Path(os.environ.get("LEGAL_ENV_FILE", PROJECT_DIR / ".env.local"))
DATA_DIR = Path(os.environ.get("LEGAL_DATA_DIR", PROJECT_DIR / "data"))

KEY_NAMES = ("TAVILY_API_KEY", "FIRECRAWL_API_KEY", "NIMBLE_API_KEY")

HTTP_TIMEOUT = float(os.environ.get("LEGAL_HTTP_TIMEOUT", "30"))
# Pause between requests to the same host (seconds). These are public agency sites; be gentle.
REQUEST_DELAY = float(os.environ.get("LEGAL_REQUEST_DELAY", "0.5"))
MAX_REDIRECTS = 5
MAX_PAGE_BYTES = 3_000_000
MAX_SECTION_CHARS = 1_500

# Government hosts. Only these are fetched; links elsewhere are dropped.
OFFICIAL_SUFFIXES = (".ny.gov", ".nyc.gov", ".irs.gov", ".treasury.gov", ".dol.gov", ".sba.gov")
OFFICIAL_HOSTS = frozenset(
    {"ny.gov", "nyc.gov", "irs.gov", "edc.nyc", "codelibrary.amlegal.com", "www.nysenate.gov", "legislation.nysenate.gov"}
)
# Official hosts that answer direct requests with 403; read through Firecrawl when a key is set.
SCRAPER_ONLY_HOSTS = frozenset({"www.nysenate.gov", "codelibrary.amlegal.com"})

# Tax year that current-year form revisions on agency sites belong to (forms posted in 2026 are for 2025).
FORM_TAX_YEAR = int(os.environ.get("LEGAL_FORM_TAX_YEAR", "2025"))


def load_env_file(path: Path | None = None) -> None:
    """Load KEY=VALUE lines into os.environ without overriding variables that are already set."""
    path = path or ENV_FILE
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
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
