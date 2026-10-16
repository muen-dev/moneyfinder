"""`kb` command line: init, seed, ingest, crawl-pending, search, embed-missing, missed, stats."""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path

from .config import KB_ROOT
from .ingest import IngestResult, SourceSpec
from .kb import KB

DEFAULT_SEEDS = KB_ROOT / "seeds" / "sources.toml"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="kb", description="moneyfinder tax-incentive knowledge base")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="apply schema.surql to the database (safe to re-run)")

    p = sub.add_parser("seed", help="crawl every seed in seeds/sources.toml")
    p.add_argument("--file", type=Path, default=DEFAULT_SEEDS)
    p.add_argument("--max-pages", type=int, default=200, help="per seed")
    p.add_argument("--refresh", action="store_true", help="re-fetch pages fetched before")

    p = sub.add_parser("ingest", help="fetch and index one URL")
    p.add_argument("url")
    p.add_argument("--authority", default="unknown")
    p.add_argument("--jurisdiction", choices=["NYS", "NYC", "federal"])
    p.add_argument("--agency")
    p.add_argument("--tag", action="append", default=[])
    p.add_argument("--force", action="store_true", help="re-chunk and re-embed even if unchanged")

    p = sub.add_parser("crawl-pending", help="fetch sources discovered through links but not fetched yet")
    p.add_argument("--limit", type=int, default=100)

    p = sub.add_parser("search", help="hybrid search over the corpus")
    p.add_argument("question")
    p.add_argument("-k", type=int, default=8)
    p.add_argument("--json", action="store_true")

    sub.add_parser("embed-missing", help="backfill embeddings for chunks that have none")

    p = sub.add_parser("missed", help="incentives a business likely qualifies for but has not claimed")
    p.add_argument("business", help="business slug, e.g. acme_bakery")
    p.add_argument("tax_year", type=int)

    sub.add_parser("stats", help="row counts")

    args = parser.parse_args(argv)
    with KB.connect() as kb:
        match args.cmd:
            case "init":
                print(f"applied {kb.db.apply_schema()} schema statements")
            case "seed":
                for seed in load_seeds(args.file):
                    print(f"\n== {seed.url} (depth {seed.depth})")
                    kb.crawl(seed, refresh=args.refresh, max_pages=args.max_pages, on_result=_print_result)
                print("\n", kb.stats())
            case "ingest":
                spec = SourceSpec(args.url, args.authority, args.jurisdiction, args.agency, args.tag)
                _print_result(kb.ingest(spec, force=args.force))
            case "crawl-pending":
                kb.ingest_pending(limit=args.limit, on_result=_print_result)
            case "search":
                hits = kb.search(args.question, k=args.k)
                if args.json:
                    print(json.dumps(hits, default=str, indent=2))
                else:
                    for i, h in enumerate(hits, 1):
                        where = h["url"] + (f" (p. {h['page']})" if h.get("page") else "")
                        print(f"\n[{i}] {h.get('title') or ''}  {where}  [{h.get('authority')}]")
                        print("    " + h["text"][:400].replace("\n", "\n    "))
            case "embed-missing":
                if not kb.embedder:
                    print("EMBED_MODEL is not set; see .env.example", file=sys.stderr)
                    return 1
                print(f"embedded {kb.embed_missing()} chunks")
            case "missed":
                print(json.dumps(kb.missed_opportunities(args.business, args.tax_year), default=str, indent=2))
            case "stats":
                print(json.dumps(kb.stats(), indent=2))
    return 0


def load_seeds(path: Path) -> list[SourceSpec]:
    data = tomllib.loads(path.read_text())
    return [SourceSpec(**entry) for entry in data["source"]]


def _print_result(r: IngestResult) -> None:
    detail = f"{r.chunks} chunks" if r.status == "new" else (r.error or "")
    links = f", {len(r.links)} links" if r.links else ""
    print(f"  {r.status:9} {r.url}  {detail}{links}", file=sys.stderr if r.status == "failed" else sys.stdout)


if __name__ == "__main__":
    raise SystemExit(main())
