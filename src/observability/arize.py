"""Arize AX tracing via OTLP (otlp.arize.com), not GraphQL."""

from __future__ import annotations

import base64
import os
from typing import Any


def validate_space_id_format(space_id: str) -> tuple[bool, str]:
    """Return (ok, decoded_or_error). Valid IDs decode to Space:<id>:<suffix>."""
    try:
        decoded = base64.b64decode(space_id).decode("utf-8")
    except Exception as exc:  # noqa: BLE001
        return False, f"not valid base64: {exc}"
    if not decoded.startswith("Space:"):
        return False, f"decoded value does not start with Space:: {decoded!r}"
    return True, decoded


def _load_dotenv(path: str = ".env") -> None:
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key, value)


def init_arize(*, project_name: str | None = None) -> Any:
    """
    Register Arize OTEL exporter using ARIZE_SPACE_ID + ARIZE_API_KEY.

    Raises ValueError if credentials are missing or Space ID format is wrong.
    """
    _load_dotenv()
    space_id = os.environ.get("ARIZE_SPACE_ID", "").strip()
    api_key = os.environ.get("ARIZE_API_KEY", "").strip()
    project = project_name or os.environ.get("ARIZE_PROJECT_NAME", "moneyfinder").strip()

    if not space_id or not api_key:
        raise ValueError("ARIZE_SPACE_ID and ARIZE_API_KEY are required")

    ok, detail = validate_space_id_format(space_id)
    if not ok:
        raise ValueError(f"Invalid ARIZE_SPACE_ID: {detail}")

    from arize.otel import register

    return register(
        space_id=space_id,
        api_key=api_key,
        project_name=project,
    )


def get_tracer(name: str = "moneyfinder"):
    from opentelemetry import trace

    return trace.get_tracer(name)
