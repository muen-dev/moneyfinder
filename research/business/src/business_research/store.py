"""Fetched mail on disk: one JSONL file per business, readable only by the local user."""

import json
import os
import shutil
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from . import config, ids
from .gmail.parse import EmailMessage


def messages_path(business_id: str) -> Path:
    return config.DATA_DIR / ids.check(business_id) / "messages.jsonl"


def write_messages(path: Path, messages: Iterable[EmailMessage]) -> int:
    """Write messages as JSONL, replacing the file only once every message has been written."""
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".partial")
    count = 0
    fd = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w") as f:
            for message in messages:
                f.write(json.dumps(message.to_dict(), ensure_ascii=False) + "\n")
                count += 1
        os.replace(partial, path)
    finally:
        partial.unlink(missing_ok=True)
    return count


def read_messages(business_id: str) -> list[dict]:
    path = messages_path(business_id)
    if not path.exists():
        return []
    with path.open() as f:
        return [json.loads(line) for line in f if line.strip()]


def fetched_at(business_id: str) -> str | None:
    path = messages_path(business_id)
    if not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat(timespec="seconds")


def delete_messages(business_id: str) -> None:
    shutil.rmtree(config.DATA_DIR / ids.check(business_id), ignore_errors=True)
