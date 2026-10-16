"""SurrealDB connection with strict error handling."""

from __future__ import annotations

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
        self._conn.signin({"username": settings.surreal_user, "password": settings.surreal_pass})
        self._conn.use(settings.surreal_ns, settings.surreal_db)

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
