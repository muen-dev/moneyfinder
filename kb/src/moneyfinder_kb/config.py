"""Settings, read from the environment. kb/.env is loaded if present."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

KB_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    surreal_url: str
    surreal_user: str
    surreal_pass: str
    surreal_ns: str
    surreal_db: str
    lake_uri: str
    aws_region: str
    embed_model: str | None
    embed_dim: int
    firecrawl_api_key: str | None

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv(KB_ROOT / ".env")
        return cls(
            surreal_url=os.getenv("SURREAL_URL", "ws://127.0.0.1:8000"),
            surreal_user=os.getenv("SURREAL_USER", "root"),
            surreal_pass=os.getenv("SURREAL_PASS", "root"),
            surreal_ns=os.getenv("SURREAL_NS", "moneyfinder"),
            surreal_db=os.getenv("SURREAL_DB", "kb"),
            lake_uri=os.getenv("LAKE_URI", str(KB_ROOT / "lake")),
            aws_region=os.getenv("AWS_REGION", "us-east-1"),
            embed_model=os.getenv("EMBED_MODEL") or None,
            embed_dim=int(os.getenv("EMBED_DIM", "1024")),
            firecrawl_api_key=os.getenv("FIRECRAWL_API_KEY") or None,
        )
