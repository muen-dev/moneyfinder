"""SurrealDB connection with strict error handling."""

from __future__ import annotations

import re
from importlib.resources import files
from typing import Any

from surrealdb import Surreal

from .config import Settings


class QueryError(RuntimeError):
    pass


def without_none(d: dict[str, Any]) -> dict[str, Any]:
    """MERGE with a None value deletes the field, so drop unknowns instead of overwriting."""
    return {k: v for k, v in d.items() if v is not None}


class DB:
    def __init__(self, settings: Settings):
        self._conn = Surreal(settings.surreal_url)
        try:
            self.auth = self._authenticate(settings)
        except Exception as e:
            raise QueryError(f"SurrealDB auth failed ({settings.describe()}): {e}") from None
        if self.auth == "root":
            self._ensure_ns_db(settings.surreal_ns, settings.surreal_db)
        self._conn.use(settings.surreal_ns, settings.surreal_db)

    def _authenticate(self, s: Settings) -> str:
        """Sign in; returns the level that worked. "auto" tries database-level, then root-level."""
        user = {"username": s.surreal_user, "password": s.surreal_pass}
        ns, db = {"namespace": s.surreal_ns}, {"namespace": s.surreal_ns, "database": s.surreal_db}
        match s.surreal_auth:
            case "none":
                return "none"
            case "token":
                self._conn.authenticate(s.surreal_token)
                return "token"
            case "root":
                self._conn.signin(user)
                return "root"
            case "namespace":
                self._conn.signin({**ns, **user})
                return "namespace"
            case "database":
                self._conn.signin({**db, **user})
                return "database"
            case "auto":
                try:
                    self._conn.signin({**db, **user})
                    return "database"
                except Exception:
                    self._conn.signin(user)
                    return "root"
        raise ValueError(f"unknown SURREAL_AUTH {s.surreal_auth!r}")

    def _ensure_ns_db(self, ns: str, db: str) -> None:
        """Root users may be pointed at a namespace/database that doesn't exist yet: create them."""
        for name in (ns, db):
            if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
                raise ValueError(f"unsafe namespace/database name {name!r}")
        resp = self._conn.query_raw(
            f"DEFINE NAMESPACE IF NOT EXISTS `{ns}`; USE NS `{ns}`; DEFINE DATABASE IF NOT EXISTS `{db}`;", {}
        )
        failed = [r["result"] for r in resp.get("result", []) if r["status"] != "OK"]
        if resp.get("error") or failed:
            raise QueryError(f"could not create ns {ns} / db {db}: {resp.get('error') or failed}")

    def run(self, sql: str, params: dict[str, Any] | None = None) -> list[Any]:
        """Run one or more statements and return each statement's result.

        Raises QueryError if any statement fails. (The SDK's query() returns only the
        first statement's result, so multi-statement queries must go through here.)
        """
        resp = self._conn.query_raw(sql, params or {})
        if resp.get("error"):
            raise QueryError(resp["error"].get("message", resp["error"]))
        results = resp["result"]
        failed = [r["result"] for r in results if r["status"] != "OK"]
        if failed:
            raise QueryError("; ".join(map(str, failed)))
        return [r["result"] for r in results]

    def one(self, sql: str, params: dict[str, Any] | None = None) -> Any:
        """Run statements and return the last statement's result."""
        return self.run(sql, params)[-1]

    def apply_schema(self) -> int:
        sql = files("moneyfinder_kb").joinpath("schema.surql").read_text()
        return len(self.run(sql))

    def close(self) -> None:
        self._conn.close()
