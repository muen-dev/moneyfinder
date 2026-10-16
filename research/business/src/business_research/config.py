"""Filesystem locations, overridable through environment variables."""

import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]  # research/business

CLIENT_SECRETS_FILE = Path(os.environ.get("GMAIL_CLIENT_SECRETS", PROJECT_DIR / "credentials.json"))
TOKEN_DIR = Path(os.environ.get("GMAIL_TOKEN_DIR", PROJECT_DIR / ".tokens"))
DATA_DIR = Path(os.environ.get("BUSINESS_DATA_DIR", PROJECT_DIR / "data"))
