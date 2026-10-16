"""Command line entry point: `uv run legal-research <command>`."""

import argparse
import json
import sys
from pathlib import Path

from . import catalog, config, export, pipeline, store


def cmd_run(args: argparse.Namespace) -> None:
    only = [p.strip() for p in args.only.split(",")] if args.only else None
    out = Path(args.out) if args.out else config.DATA_DIR
    print("Building the tax-credit catalog ...", file=sys.stderr)
    result = pipeline.run(
        out_dir=out, pages=not args.no_pages, with_claims=not args.no_claims, search=args.search, only=only,
        log=lambda message: print(f"  {message}", file=sys.stderr),
    )
    programs = result["programs"]
    by_status = {s: sum(p["status"] == s for p in programs) for s in catalog.STATUSES}
    print(f"\n{len(programs)} programs ({', '.join(f'{n} {s}' for s, n in by_status.items())}), "
          f"{sum(len(n['programs']) > 0 for n in result['niches'])} niches with programs, "
          f"{len(result['unmatched_claims'])} claimed credits without a program page, {len(result['candidates'])} search leads")
    print(f"Wrote {store.catalog_path(out)} (pages in {out / 'pages'})")


def _load(args) -> dict:
    result = store.read_catalog(Path(args.out) if args.out else None)
    if result is None:
        raise FileNotFoundError("no catalog yet; run: legal-research run")
    return result


def cmd_show(args: argparse.Namespace) -> None:
    result = _load(args)
    programs = {p["id"]: p for p in result["programs"]}
    if args.program:
        program = programs.get(args.program)
        if program is None:
            raise ValueError(f"no program {args.program!r}; ids are listed by: legal-research show")
        print(json.dumps(program, indent=2, ensure_ascii=False))
        return
    niches = [n for n in result["niches"] if not args.niche or n["id"] == args.niche]
    if args.niche and not niches:
        raise ValueError(f"no niche {args.niche!r}; see: legal-research niches")
    if args.json:
        print(json.dumps({"niches": niches, "programs": [programs[i] for n in niches for i in n["programs"]]}, indent=2, ensure_ascii=False))
        return
    print(f"Tax-credit catalog, generated {result['generated_at']}\n")
    for niche in niches:
        if not niche["programs"]:
            continue
        print(f"{niche['label']}  [{niche['id']}]")
        for pid in sorted(niche["programs"], key=lambda i: _claimants(programs[i])):
            print("  " + _line(programs[pid]))
        print()
    if not args.niche:
        untagged = [p for p in programs.values() if not p["niches"]]
        if untagged:
            print("No niche (general or not yet tagged)")
            for p in sorted(untagged, key=_claimants):
                print("  " + _line(p))


def _claimants(program: dict) -> float:
    counts = [c["taxpayers"] for c in program.get("claims") or [] if c.get("taxpayers") is not None]
    return min(counts) if counts else float("inf")


def _line(p: dict) -> str:
    claims = (p.get("claims") or [None])[0]
    usage = ""
    if claims and claims.get("taxpayers") is not None:
        avg = f", avg ${claims['average']:,}" if claims.get("average") else ""
        usage = f"{claims['taxpayers']:,} claimants {claims['latest_year']}{avg}"
    forms = " ".join(f["code"] for f in (p.get("facts") or {}).get("forms", []))[:30]
    flag = " needs certificate" if p.get("requires_preapproval") else ""
    return f"{p['id']:<38} {p['jurisdiction']:<7} {p['status']:<7} {usage:<36} {forms:<30}{flag}  {p['name'][:60]}"


def cmd_niches(args: argparse.Namespace) -> None:
    for niche in _load(args)["niches"]:
        print(f"{niche['id']:<28} {len(niche['programs']):>3}  {niche['label']}")


def cmd_links(args: argparse.Namespace) -> None:
    """Every official link in the catalog, one per line: program, authority, url."""
    for program in _load(args)["programs"]:
        rows = [("page", program["url"])]
        facts = program.get("facts") or {}
        for form in facts.get("forms", []):
            rows += [("form", form.get("pdf")), ("form_instructions", form.get("instructions"))]
        rows += [(link["authority"], link["url"]) for link in [*facts.get("links", []), *program.get("links", [])]]
        for authority, url in rows:
            if url and (not args.authority or authority == args.authority):
                print(f"{program['id']}\t{authority}\t{url}")


def cmd_seeds(args: argparse.Namespace) -> None:
    result = _load(args)
    path = Path(args.file) if args.file else (Path(args.out) if args.out else config.DATA_DIR) / "kb-seeds.toml"
    store.write_text(path, export.kb_seeds(result))
    print(f"Wrote {len(export.seed_entries(result))} seeds to {path}")


def cmd_load_kb(args: argparse.Namespace) -> None:
    from moneyfinder_kb import KB  # needs a running SurrealDB, so imported only here

    result = _load(args)
    with KB.connect() as kb:
        export.load_kb(result, kb, args.tax_year, log=print)


def cmd_keys(args: argparse.Namespace) -> None:
    for name, present in config.keys_present().items():
        print(f"{name}\t{'set' if present else 'missing'}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="legal-research", description="Tax-credit program catalog for moneyfinder.")
    parser.add_argument("--out", help=f"data folder (default: {config.DATA_DIR})")
    commands = parser.add_subparsers(required=True)

    run = commands.add_parser("run", help="find programs, read their official pages, attach claim counts, tag niches")
    run.add_argument("--only", help="comma-separated program ids (after discovery)")
    run.add_argument("--no-pages", action="store_true", help="skip reading program pages (links only)")
    run.add_argument("--no-claims", action="store_true", help="skip data.ny.gov claim counts")
    run.add_argument("--search", action="store_true", help="also search (Tavily/Nimble) for niche programs the indexes miss")
    run.set_defaults(func=cmd_run)

    show = commands.add_parser("show", help="print programs by niche, fewest claimants first")
    show.add_argument("program", nargs="?", help="print one program in full")
    show.add_argument("--niche", help="only this niche")
    show.add_argument("--json", action="store_true")
    show.set_defaults(func=cmd_show)

    commands.add_parser("niches", help="list niches and how many programs each has").set_defaults(func=cmd_niches)

    links = commands.add_parser("links", help="every official link: program, authority, url")
    links.add_argument("--authority", help="only this kind, e.g. form, form_instructions, statute, program_page")
    links.set_defaults(func=cmd_links)

    seeds = commands.add_parser("seeds", help="write the catalog's links as a kb seeds file")
    seeds.add_argument("--file", help="output path (default: <data>/kb-seeds.toml)")
    seeds.set_defaults(func=cmd_seeds)

    load = commands.add_parser("load-kb", help="write programs and forms into the kb's incentive and form tables")
    load.add_argument("--tax-year", type=int, default=config.FORM_TAX_YEAR, help="tax year of the current forms")
    load.set_defaults(func=cmd_load_kb)

    commands.add_parser("keys", help="show which API keys are configured (never prints values)").set_defaults(func=cmd_keys)

    args = parser.parse_args(argv)
    try:
        args.func(args)
    except (catalog.CatalogError, FileNotFoundError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
