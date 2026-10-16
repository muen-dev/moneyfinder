#!/usr/bin/env python3
"""Verify Arize Space ID + API key via OTLP (correct method — not GraphQL)."""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.observability.arize import get_tracer, init_arize, validate_space_id_format
import os


def main() -> int:
    # Load .env into process
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k, v)

    space = os.environ.get("ARIZE_SPACE_ID", "")
    ok, detail = validate_space_id_format(space)
    print(f"Space ID format: {'OK' if ok else 'FAIL'} ({detail})")
    if not ok:
        return 1

    print(f"Project: {os.environ.get('ARIZE_PROJECT_NAME', 'moneyfinder')}")
    print("Registering OTEL exporter → otlp.arize.com …")

    try:
        init_arize()
    except Exception as exc:  # noqa: BLE001
        print(f"Register failed: {exc}")
        return 1

    tracer = get_tracer("moneyfinder-smoke")
    with tracer.start_as_current_span("moneyfinder_arize_smoke") as span:
        span.set_attribute("app", "moneyfinder")
        span.set_attribute("check", "space_id_and_api_key")
        span.set_attribute("pipeline", "b2b_unclaimed_funds")
        print(f"Span started: {span.get_span_context().span_id}")

    # Allow exporter flush
    time.sleep(2)
    print("Span exported (or queued).")
    print("Open Arize AX → your Space → project 'moneyfinder' within ~30s.")
    print("If the span appears, credentials are verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
