"""AWS Bedrock runtime configuration helpers (no secrets logged)."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class BedrockRuntimeConfig:
    region: str
    model_id: str
    prompt_version: str = "v1-b2b-unclaimed"


def load_bedrock_config() -> BedrockRuntimeConfig:
    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-west-2"
    model_id = os.getenv("AWS_BEDROCK_MODEL_ID", "anthropic.claude-sonnet-4-6")
    return BedrockRuntimeConfig(region=region, model_id=model_id)


def tool_call_log_entry(tool_name: str, ok: bool, meta: dict | None = None) -> dict:
    """Structured log shape for Arize / local tracing. Never include secrets."""
    safe_meta = {k: v for k, v in (meta or {}).items() if "key" not in k.lower() and "token" not in k.lower()}
    return {
        "tool": tool_name,
        "ok": ok,
        "meta": safe_meta,
        "prompt_version": load_bedrock_config().prompt_version,
        "model_id": load_bedrock_config().model_id,
    }
