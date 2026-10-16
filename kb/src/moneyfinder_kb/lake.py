"""Content-addressed object store for everything we fetch: a local folder or S3.

Layout (identical in both backends):
    raw/sha256/ab/abcdef...          original bytes, never modified
    raw/sha256/ab/abcdef....json     sidecar: url, content type, fetched_at, ...
    text/sha256/cd/cdef01....md      extracted markdown (derived, rebuildable)

Keys are hashes, so re-fetching an unchanged page writes nothing new, and the lake
can be scanned without the database (e.g. DuckDB over raw/**/*.json).
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Protocol


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def raw_key(digest: str) -> str:
    return f"raw/sha256/{digest[:2]}/{digest}"


def text_key(digest: str) -> str:
    return f"text/sha256/{digest[:2]}/{digest}.md"


class Lake(Protocol):
    def exists(self, key: str) -> bool: ...
    def put(self, key: str, data: bytes, content_type: str) -> None: ...
    def get(self, key: str) -> bytes: ...


class LocalLake:
    def __init__(self, root: Path):
        self.root = root

    def exists(self, key: str) -> bool:
        return (self.root / key).exists()

    def put(self, key: str, data: bytes, content_type: str) -> None:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        # Write then rename, so a crash never leaves a partial object under a valid key.
        fd, tmp = tempfile.mkstemp(dir=path.parent)
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, path)

    def get(self, key: str) -> bytes:
        return (self.root / key).read_bytes()


class S3Lake:
    def __init__(self, bucket: str, prefix: str, region: str):
        import boto3

        self.bucket = bucket
        self.prefix = prefix.strip("/")
        self._s3 = boto3.client("s3", region_name=region)

    def _key(self, key: str) -> str:
        return f"{self.prefix}/{key}" if self.prefix else key

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError

        try:
            self._s3.head_object(Bucket=self.bucket, Key=self._key(key))
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] in ("404", "NoSuchKey", "NotFound"):
                return False
            raise

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self._s3.put_object(Bucket=self.bucket, Key=self._key(key), Body=data, ContentType=content_type)

    def get(self, key: str) -> bytes:
        return self._s3.get_object(Bucket=self.bucket, Key=self._key(key))["Body"].read()


def open_lake(uri: str, region: str) -> Lake:
    if uri.startswith("s3://"):
        bucket, _, prefix = uri.removeprefix("s3://").partition("/")
        return S3Lake(bucket, prefix, region)
    return LocalLake(Path(uri).expanduser())


def put_raw(lake: Lake, data: bytes, content_type: str, meta: dict[str, Any]) -> str:
    """Store original bytes plus a JSON sidecar. Returns the raw key."""
    digest = sha256(data)
    key = raw_key(digest)
    if not lake.exists(key):
        lake.put(key, data, content_type)
    lake.put(f"{key}.json", json.dumps({"sha256": digest, **meta}, indent=2).encode(), "application/json")
    return key
