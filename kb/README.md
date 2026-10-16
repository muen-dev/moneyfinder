# kb: tax-incentive data lake + knowledge base

Everything our agents know about New York tax incentives, stored so they can find it fast and cite it.

```
 fetch (httpx, Firecrawl)          extract + chunk            embed (Bedrock Titan V2)
 tax.ny.gov, esd.ny.gov, nyc.gov ─► PDF/HTML → markdown ─► 1,800-char chunks ─► 1024-d vectors
        │                                   │                                       │
        ▼                                   ▼                                       ▼
 ┌─────────────── LAKE (folder or S3) ──────────────┐   ┌──────────── SurrealDB 3.x ──────────────────┐
 │ raw/sha256/…        original bytes, immutable    │   │ source ─fetched→ document ←─ chunk          │
 │ raw/sha256/….json   url, fetched_at, type        │   │   (version history)      (BM25 + HNSW)      │
 │ text/sha256/….md    extracted markdown           │   │ incentive ─uses_form→ form                  │
 └──────────────────────────────────────────────────┘   │ incentive|criterion|form ─cites→ chunk      │
                                                        │ business ─eligible_for→ incentive (by year) │
                                                        │ business ─claimed→ incentive  (by year)     │
                                                        └─────────────────────────────────────────────┘
```

- **Lake** holds every byte we fetched, addressed by hash. It's the source of truth: the database can be rebuilt from it, and re-fetching an unchanged page writes nothing.
- **SurrealDB** holds the index and the structured facts. It handles tables, graph edges, full-text and vector search together, so one query can go from "question" to "matching passage" to "which credit and form it belongs to."
- **Provenance**: every structured fact (`incentive`, `criterion`, `form`) links to the `chunk`s it came from, and every chunk knows its URL, page and fetch date. When a page changes, the old version is kept for audit and dropped from search.

## Connection

`kb` reads the repo-root `.env` (shared SurrealDB Cloud: `SURREAL_WS_URL`, `SURREAL_NAMESPACE=moneyfinder`,
`SURREAL_DATABASE=main`, `SURREAL_USER`/`SURREAL_PASS` or a JWT in `SURREAL_TOKEN`). On a remote URL it signs in
database-level first and falls back to a root-level system user, which also creates the namespace and database if missing. `kb/.env`
overrides it per key, and exported variables beat both, so a local database still works: put
`SURREAL_URL=ws://127.0.0.1:8000`, `SURREAL_DATABASE=kb` (root/root signin is the local default) in `kb/.env`.
`uv run kb ping` shows where it connects and how (never the secrets). `SURREAL_AUTH=root|namespace|database|token`
forces the signin level. See `src/moneyfinder_kb/config.py`.

## Dossiers (per-business, for the form filler)

```bash
uv run kb dossier-push themaincapital.com     # a path, slug or domain under research/*/data/; --all for every one
uv run kb dossier-get themaincapital-com      # RETURN fn::business_dossier('themaincapital-com')
```

A push upserts `business:<slug>` (typed columns, `profile`, the whole JSON in `dossier`), replaces its `fact` rows,
inserts missing `incentive`/`form`/`source` rows and `uses_form` links, and writes one `eligible_for` edge per credit
for last year (stale dossier edges are removed). One transaction; re-running it changes nothing.
See [docs/FORM_FILLER_HANDOFF.md](../docs/FORM_FILLER_HANDOFF.md).

Tests: `uv run pytest -q` (uses the SDK's in-process engine; no server).

## Quickstart (local database)

```bash
cd kb
uv sync
cp .env.example .env              # add FIRECRAWL_API_KEY; set EMBED_MODEL once Bedrock access is set up

docker compose up -d              # or: surreal start --user root --pass root rocksdb://./.surreal-data/kb.db
uv run kb init                    # apply schema (safe to re-run)
uv run kb seed --max-pages 50     # crawl seeds/sources.toml
uv run kb crawl-pending           # fetch links discovered during the crawl
uv run kb search "credit for hiring veterans"
uv run kb stats
```

Without `EMBED_MODEL`, search is full-text only. Set it later and run `uv run kb embed-missing` to backfill vectors.

## From agent code

```python
from moneyfinder_kb import KB
from surrealdb import RecordID

with KB.connect() as kb:
    hits = kb.search("Excelsior jobs credit per new job", k=5)    # text, url, page, authority, incentives

    # research agent: turn passages into structured facts, citing them
    kb.upsert_incentive("excelsior_jobs", name="Excelsior Jobs Program tax credit", kind="credit",
                        jurisdiction="NYS", requires_preapproval=True, status="active")
    kb.cite(RecordID("incentive", "excelsior_jobs"), [hits[0]["chunk"]])
    kb.upsert_form("CT-607", 2025, instructions="https://www.tax.ny.gov/pdf/current_forms/ct/ct607i.pdf")
    kb.link_form("excelsior_jobs", "CT-607", 2025)

    # matching agent: one verdict per business, incentive and tax year (re-assessing replaces it)
    kb.upsert_business("acme_bakery", name="Acme Bakery", nyc_borough="Brooklyn", employees=14)
    kb.assess("acme_bakery", "excelsior_jobs", 2025, "likely", confidence=0.8,
              reasons=["adding 6 jobs"], evidence=[hits[0]["chunk"]])

    kb.missed_opportunities("acme_bakery", 2025)   # likely/possible, not yet claimed
    kb.record_claim("acme_bakery", "excelsior_jobs", 2025, "filed", amount=4100, form=("CT-607", 2025))
    kb.incentive("excelsior_jobs")                 # with forms, criteria and cited passages
```

The same queries are stored in the database as `fn::search_chunks` and `fn::missed_opportunities`, so a TypeScript agent or the SurrealDB MCP server can call them without this package.

## Adding sources

Add an entry to [seeds/sources.toml](seeds/sources.toml): a URL, its `authority` (statute, form, agency_guidance, ...), and optional `follow` regexes and `depth` for crawling its links. The crawler obeys robots.txt and only follows links matching `follow`. One-off: `uv run kb ingest <url> --authority form --jurisdiction NYS`.

## Scaling up

| Concern | Today | When it grows |
|---|---|---|
| Raw storage | `kb/lake/` folder | `LAKE_URI=s3://bucket/prefix`; same layout, no code change |
| Database | SurrealDB Cloud (root `.env`) or local | `kb/.env` picks the database; see Connection |
| Re-crawls | text-hash dedupe skips re-chunking and re-embedding unchanged pages | schedule `kb seed` plus `kb crawl-pending` |
| Vector memory | HNSW index at 1024 dimensions ≈ 4 KB per chunk (1M chunks ≈ 4 GB) | drop to 512 dimensions: change `chunk_vec` and `EMBED_DIM` together |
| Crawl throughput | one worker, 0.5 s delay per request | `crawl-pending` has no row locking, so shard parallel workers by domain |
| Lake analytics | | DuckDB over `raw/**/*.json` sidecars, no database needed |

## Not here yet

- Extracting structured facts from passages (incentive fields, criteria, form line items). That's the research agent's job, using Bedrock and writing through the methods above.
- Per-business conversation memory. That belongs in SurrealDB Agent Memory, scoped per business, alongside this shared corpus.
