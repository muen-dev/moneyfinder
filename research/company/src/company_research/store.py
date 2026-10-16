"""Profiles and raw API responses on disk, readable only by the local user (0700 dirs, 0600 files)."""

import json
import os
import re
import shutil
from pathlib import Path

from . import config
from .domain import slug


def default_dir(domain: str) -> Path:
    return config.DATA_DIR / slug(domain)


def profile_path(out_dir: Path) -> Path:
    return out_dir / "profile.json"


def write_run(out_dir: Path, profile: dict, calls: list[dict]) -> Path:
    """Replace the profile and its raw responses in out_dir."""
    _private_dir(out_dir)
    raw = out_dir / "raw"
    shutil.rmtree(raw, ignore_errors=True)
    _private_dir(raw)
    for i, call in enumerate(calls, 1):
        endpoint = re.sub(r"[^a-z0-9]+", "-", call.get("endpoint", "").lower().split("//")[-1])[-60:].strip("-")
        write_json(raw / f"{i:02d}-{call.get('provider', 'call')}-{endpoint}.json", call)
    path = profile_path(out_dir)
    write_json(path, profile)
    return path


def read_profile(out_dir: Path) -> dict | None:
    path = profile_path(out_dir)
    if not path.exists():
        return None
    return json.loads(path.read_text())


def write_json(path: Path, data) -> None:
    """Atomic owner-only write."""
    partial = path.with_name(path.name + ".partial")
    fd = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        os.replace(partial, path)
    finally:
        partial.unlink(missing_ok=True)


def _private_dir(path: Path) -> None:
    """Create path and any missing parents as 0700 (mkdir -p would leave parents at the umask)."""
    missing = []
    while not path.exists():
        missing.append(path)
        path = path.parent
    for directory in reversed(missing):
        directory.mkdir(mode=0o700, exist_ok=True)
        os.chmod(directory, 0o700)
