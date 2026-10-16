"""The one object agents use: search the corpus, ingest sources, read and write tax knowledge."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from urllib.parse import urlsplit

from surrealdb import RecordID

from .config import Settings
from .db import DB, without_none
from .dossier import PUSH_SQL, build_push, push_summary
from .embed import Embedder, make_embedder
from .ingest import IngestResult, SourceSpec, crawl, ingest_pending, ingest_url, normalize_url
from .lake import Lake, open_lake


class KB:
    def __init__(self, settings: Settings, db: DB, lake: Lake, embedder: Embedder | None):
        self.settings = settings
        self.db = db
        self.lake = lake
        self.embedder = embedder

    @classmethod
    def connect(cls, settings: Settings | None = None) -> KB:
        settings = settings or Settings.from_env()
        return cls(
            settings,
            DB(settings),
            open_lake(settings.lake_uri, settings.aws_region),
            make_embedder(settings),
        )

    def close(self) -> None:
        self.db.close()

    def __enter__(self) -> KB:
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # ─── Retrieval ───────────────────────────────────────────────────────────

    def search(self, question: str, k: int = 8) -> list[dict[str, Any]]:
        """Hybrid full-text + vector search over current documents. Each hit has text, url, authority, page."""
        embedding = self.embedder.embed([question])[0] if self.embedder else None
        return self.db.one("RETURN fn::search_chunks($q, $e, $k);", {"q": question, "e": embedding, "k": k})

    def incentive(self, slug: str) -> dict[str, Any] | None:
        """An incentive with its forms, eligibility criteria and the source passages it cites."""
        return self.db.one(
            """
            SELECT *,
                ->uses_form.{ role, form: out.{ code, tax_year, title, pdf: pdf.url, instructions: instructions.url } } AS forms,
                (SELECT kind, text, rule, required FROM criterion WHERE incentive = $parent.id) AS criteria,
                ->cites->chunk.{ text, url: document.origin.url, page } AS citations
            FROM ONLY $id;
            """,
            {"id": RecordID("incentive", slug)},
        )

    def missed_opportunities(self, business: str, tax_year: int) -> list[dict[str, Any]]:
        return self.db.one(
            "RETURN fn::missed_opportunities($b, $y);", {"b": RecordID("business", business), "y": tax_year}
        )

    # ─── Ingestion ───────────────────────────────────────────────────────────

    def ingest(self, spec: SourceSpec | str, force: bool = False) -> IngestResult:
        return ingest_url(self, SourceSpec(spec) if isinstance(spec, str) else spec, force=force)

    def crawl(self, seed: SourceSpec, **kwargs) -> list[IngestResult]:
        return crawl(self, seed, **kwargs)

    def ingest_pending(self, **kwargs) -> list[IngestResult]:
        return ingest_pending(self, **kwargs)

    def is_fetched(self, url: str) -> bool:
        current = self.db.one("SELECT VALUE current FROM ONLY $s;", {"s": RecordID("source", normalize_url(url))})
        return current is not None

    def embed_missing(self, batch: int = 128) -> int:
        """Backfill vectors for chunks ingested before embeddings were enabled."""
        if not self.embedder:
            raise RuntimeError("Set EMBED_MODEL to enable embeddings")
        total = 0
        while rows := self.db.one("SELECT id, text FROM chunk WHERE embedding = NONE LIMIT $n;", {"n": batch}):
            vectors = self.embedder.embed([r["text"] for r in rows])
            self.db.run(
                "FOR $r IN $rows { UPDATE $r.id SET embedding = $r.embedding RETURN NONE; };",
                {"rows": [{"id": r["id"], "embedding": v} for r, v in zip(rows, vectors, strict=False)]},
            )
            total += len(rows)
        return total

    # ─── Tax knowledge (written by research agents) ────────────────────────────

    def upsert_incentive(self, slug: str, **fields: Any) -> dict[str, Any]:
        """e.g. upsert_incentive("excelsior_jobs", name=..., kind="credit", jurisdiction="NYS")"""
        return self._merge(RecordID("incentive", slug), fields)

    def upsert_form(self, code: str, tax_year: int, **fields: Any) -> dict[str, Any]:
        """pdf / instructions may be URLs; unseen ones are queued as sources for `kb crawl-pending`."""
        for key, authority in (("pdf", "form"), ("instructions", "form_instructions")):
            if isinstance(fields.get(key), str):
                url = normalize_url(fields[key])
                fields[key] = RecordID("source", url)
                self.db.run(
                    "INSERT IGNORE INTO source {id: $id, url: $url, domain: $domain, authority: $authority} RETURN NONE;",
                    {"id": fields[key], "url": url, "domain": urlsplit(url).netloc, "authority": authority},
                )
        return self._merge(RecordID("form", [code, tax_year]), {"code": code, "tax_year": tax_year, **fields})

    def link_form(self, incentive: str, code: str, tax_year: int, role: str = "claim") -> None:
        self.db.run(
            "INSERT RELATION INTO uses_form {in: $i, out: $f, role: $role} ON DUPLICATE KEY UPDATE role = $input.role RETURN NONE;",
            {"i": RecordID("incentive", incentive), "f": RecordID("form", [code, tax_year]), "role": role},
        )

    def add_criterion(
        self,
        incentive: str,
        kind: str,
        text: str,
        rule: dict | None = None,
        required: bool = True,
        evidence: list[RecordID] = (),
    ) -> RecordID:
        row = self.db.one(
            "CREATE ONLY criterion CONTENT $data;",
            {
                "data": without_none(
                    {
                        "incentive": RecordID("incentive", incentive),
                        "kind": kind,
                        "text": text,
                        "rule": rule,
                        "required": required,
                    }
                )
            },
        )
        self.cite(row["id"], evidence)
        return row["id"]

    def cite(self, record: RecordID, chunks: list[RecordID], quote: str | None = None) -> None:
        """Attach provenance: `record` (incentive, criterion or form) was derived from these chunks."""
        if not chunks:
            return
        edges = [without_none({"in": record, "out": c, "quote": quote}) for c in chunks]
        self.db.run(
            "INSERT RELATION INTO cites $e ON DUPLICATE KEY UPDATE quote = $input.quote RETURN NONE;", {"e": edges}
        )

    # ─── Businesses (written by assessment and filing agents) ─────────────────

    def upsert_business(self, slug: str, **fields: Any) -> dict[str, Any]:
        if "annual_revenue" in fields:
            fields["annual_revenue"] = _decimal(fields["annual_revenue"])
        return self._merge(RecordID("business", slug), fields)

    def assess(
        self,
        business: str,
        incentive: str,
        tax_year: int,
        status: str,
        confidence: float | None = None,
        reasons: list[str] = (),
        missing_info: list[str] = (),
        evidence: list[RecordID] = (),
        estimated_value: float | Decimal | None = None,
        assessed_by: str | None = None,
    ) -> None:
        """Record (or replace) the eligibility verdict for one business, incentive and tax year."""
        edge = without_none(
            {
                "in": RecordID("business", business),
                "out": RecordID("incentive", incentive),
                "tax_year": tax_year,
                "status": status,
                "confidence": confidence,
                "reasons": list(reasons),
                "missing_info": list(missing_info),
                "evidence": list(evidence),
                "estimated_value": _decimal(estimated_value),
                "assessed_by": assessed_by,
            }
        )
        self.db.run(
            """
            INSERT RELATION INTO eligible_for $e ON DUPLICATE KEY UPDATE
                status = $input.status, confidence = $input.confidence, reasons = $input.reasons,
                missing_info = $input.missing_info, evidence = $input.evidence,
                estimated_value = $input.estimated_value, assessed_by = $input.assessed_by
            RETURN NONE;
            """,
            {"e": edge},
        )

    def record_claim(
        self,
        business: str,
        incentive: str,
        tax_year: int,
        status: str,
        amount: float | Decimal | None = None,
        form: tuple[str, int] | None = None,
    ) -> None:
        edge = without_none(
            {
                "in": RecordID("business", business),
                "out": RecordID("incentive", incentive),
                "tax_year": tax_year,
                "status": status,
                "amount": _decimal(amount),
                "form": RecordID("form", list(form)) if form else None,
            }
        )
        self.db.run(
            """
            INSERT RELATION INTO claimed $e ON DUPLICATE KEY UPDATE
                status = $input.status, amount = $input.amount, form = $input.form
            RETURN NONE;
            """,
            {"e": edge},
        )

    # ─── Dossiers (research/ output; read by the form filler) ────────────────

    def push_dossier(self, dossier: dict[str, Any], tax_year: int | None = None) -> dict[str, Any]:
        """Upsert business:<slug>, replace its facts, link its credits and forms. Idempotent, one transaction."""
        params = build_push(dossier, tax_year)
        self.db.run(PUSH_SQL, params)
        return push_summary(params)

    def business_dossier(self, slug: str) -> dict[str, Any] | None:
        """fn::business_dossier: business columns + profile, facts with provenance, credits with forms."""
        return self.db.one("RETURN fn::business_dossier($slug);", {"slug": slug})

    # ─── Housekeeping ────────────────────────────────────────────────────────

    def stats(self) -> dict[str, int]:
        return self.db.one(
            """
            RETURN {
                sources:    (SELECT count() FROM source GROUP ALL)[0].count ?? 0,
                pending:    (SELECT count() FROM source WHERE current = NONE GROUP ALL)[0].count ?? 0,
                failed:     (SELECT count() FROM source WHERE last_error != NONE GROUP ALL)[0].count ?? 0,
                documents:  (SELECT count() FROM document WHERE superseded_at = NONE GROUP ALL)[0].count ?? 0,
                chunks:     (SELECT count() FROM chunk GROUP ALL)[0].count ?? 0,
                embedded:   (SELECT count() FROM chunk WHERE embedding != NONE GROUP ALL)[0].count ?? 0,
                incentives: (SELECT count() FROM incentive GROUP ALL)[0].count ?? 0,
                forms:      (SELECT count() FROM form GROUP ALL)[0].count ?? 0,
                businesses: (SELECT count() FROM business GROUP ALL)[0].count ?? 0,
                facts:      (SELECT count() FROM fact GROUP ALL)[0].count ?? 0,
            };
            """
        )

    def _merge(self, rid: RecordID, fields: dict[str, Any]) -> dict[str, Any]:
        return self.db.one("UPSERT ONLY $id MERGE $data;", {"id": rid, "data": without_none(fields)})


def _decimal(x: float | Decimal | None) -> Decimal | None:
    return None if x is None else Decimal(str(x))
