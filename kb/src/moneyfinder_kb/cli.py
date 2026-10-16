"""`kb` command line: init, ping, seed, ingest, crawl-pending, search, embed-missing, missed, stats,
dossier-push, dossier-get."""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path

from .config import KB_ROOT, Settings
from .db import QueryError
from .dossier import find_dossiers, load_dossier, resolve_dossier, slugify, to_jsonable
from .ingest import IngestResult, SourceSpec
from .kb import KB

DEFAULT_SEEDS = KB_ROOT / "seeds" / "sources.toml"


def main(argv: list[str] | None = None) -> int:
    try:
        return _main(argv)
    except (ValueError, FileNotFoundError, QueryError) as e:
        print(f"kb: {e}", file=sys.stderr)
        return 1


def _main(argv: list[str] | None = None) -> int:
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

    sub.add_parser("ping", help="check the SurrealDB connection and credentials (prints no secrets)")

    p = sub.add_parser("dossier-push", help="load research/ dossier.json files into business, fact, eligible_for")
    p.add_argument("dossier", nargs="*", help="path to dossier.json, or a slug/domain found under research/*/data/")
    p.add_argument("--all", action="store_true", help="every research/*/data/**/dossier.json")
    p.add_argument("--tax-year", type=int, help="default: last calendar year")

    p = sub.add_parser("dossier-get", help="print fn::business_dossier(<slug>) as JSON")
    p.add_argument("slug", help="e.g. themaincapital-com (a domain also works)")

    args = parser.parse_args(argv)
    if args.cmd == "dossier-push":
        paths = find_dossiers() if args.all else [resolve_dossier(a) for a in args.dossier]
        if not paths:
            parser.error("give a dossier path/slug, or --all")
    settings = Settings.from_env()
    with KB.connect(settings) as kb:
        match args.cmd:
            case "init":
                print(f"applied {kb.db.apply_schema()} schema statements to {settings.describe()} (signed in: {kb.db.auth})")
            case "ping":
                info = kb.db.one("RETURN { fn: (INFO FOR DB).functions.keys(), tables: (INFO FOR DB).tables.keys() };")
                print(f"ok: {settings.describe()} (signed in: {kb.db.auth})")
                print(f"  tables: {', '.join(sorted(info['tables'])) or '(none: run kb init)'}")
                print(f"  functions: {', '.join(sorted(info['fn'])) or '(none)'}")
            case "dossier-push":
                for path in paths:
                    summary = kb.push_dossier(load_dossier(path), tax_year=args.tax_year)
                    print(json.dumps({"file": str(path), **summary}))
            case "dossier-get":
                result = kb.business_dossier(args.slug)
                if not (result or {}).get("business") and slugify(args.slug) != args.slug:
                    result = kb.business_dossier(slugify(args.slug))  # a domain was given
                print(json.dumps(to_jsonable(result), default=str, indent=2))
                if not result or not result.get("business"):
                    print(f"no business:{args.slug} (push it with: kb dossier-push {args.slug})", file=sys.stderr)
                    return 1
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
