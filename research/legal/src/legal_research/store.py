"""The catalog and fetched pages on disk, written atomically (0700 dirs, 0600 files, like research/company)."""

import json
import os
from pathlib import Path

from . import config


def catalog_path(out_dir: Path | None = None) -> Path:
    return (out_dir or config.DATA_DIR) / "catalog.json"


def read_catalog(out_dir: Path | None = None) -> dict | None:
    path = catalog_path(out_dir)
    return json.loads(path.read_text()) if path.exists() else None


def write_json(path: Path, data) -> None:
    write_text(path, json.dumps(data, indent=2, ensure_ascii=False, default=str))


def write_text(path: Path, text: str) -> None:
    """Atomic owner-only write."""
    private_dir(path.parent)
    partial = path.with_name(path.name + ".partial")
    fd = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
        os.replace(partial, path)
    finally:
        partial.unlink(missing_ok=True)


def private_dir(path: Path) -> None:
    """Create path and any missing parents as 0700 (mkdir -p would leave parents at the umask)."""
    missing = []
    while not path.exists():
        missing.append(path)
        path = path.parent
    for directory in reversed(missing):
        directory.mkdir(mode=0o700, exist_ok=True)
        os.chmod(directory, 0o700)
