"""Ensure the moneyfinder repo root is importable as `src.*` from the business package."""

from __future__ import annotations

import sys
from pathlib import Path

# wallet/_repo.py → wallet → business_research → src → business → research → repo
REPO_ROOT = Path(__file__).resolve().parents[5]


def ensure_repo_on_path() -> Path:
    root = str(REPO_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    return REPO_ROOT
