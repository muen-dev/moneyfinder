"""Command line entry point: `uv run company-research <command>`."""

import argparse
import json
import sys
from pathlib import Path

from . import config, domain, pipeline, store, synthesize
from .profile import FIELDS


def cmd_run(args: argparse.Namespace) -> None:
    only = [name.strip() for name in args.only.split(",")] if args.only else None
    unknown = set(only or []) - set(pipeline.COLLECTORS)
    if unknown:
        raise ValueError(f"unknown collector(s): {', '.join(sorted(unknown))} (choose from {', '.join(pipeline.COLLECTORS)})")
    normalized = domain.normalize(args.domain)
    out = Path(args.out) if args.out else store.default_dir(normalized)
    print(f"Researching {normalized} ...", file=sys.stderr)
    profile = pipeline.research(
        normalized,
        business_id=args.business_id,
        contact_email=args.email,
        out_dir=out,
        use_llm=not args.no_llm,
        only=only,
        log=lambda message: print(f"  {message}", file=sys.stderr),
    )
    _print_summary(profile)
    print(f"\nWrote {store.profile_path(out)} (raw API responses in {out / 'raw'})")


def cmd_show(args: argparse.Namespace) -> None:
    normalized = domain.normalize(args.domain)
    out = Path(args.out) if args.out else store.default_dir(normalized)
    profile = store.read_profile(out)
    if profile is None:
        raise FileNotFoundError(f"no profile for {normalized} yet; run: company-research run {normalized}")
    if args.json:
        print(json.dumps(profile, indent=2, ensure_ascii=False))
    else:
        _print_summary(profile)


def cmd_check(args: argparse.Namespace) -> None:
    print(domain.normalize(args.domain))


def cmd_keys(args: argparse.Namespace) -> None:
    for name, present in config.keys_present().items():
        print(f"{name}\t{'set' if present else 'missing'}")
    print(f"AWS credentials (optional LLM step)\t{'found' if synthesize.available() else 'missing'}")


def _print_summary(profile: dict) -> None:
    print(f"\n{profile['domain']}  (generated {profile['generated_at']})")
    for name, info in profile["collectors"].items():
        error = f"  {info['error']}" if info.get("error") else ""
        print(f"  {name:<14} {info['status']:<8} {info['facts']:>3} facts {info['duration_s']:>6}s{error}")
    print()
    for name, claims in profile["fields"].items():
        label, multi = FIELDS[name]
        values = claims if multi else claims[:1]
        for i, claim in enumerate(values[:5]):
            value = claim["value"]
            if isinstance(value, dict):
                value = value.get("title") or value.get("code") or json.dumps(value)
            if isinstance(value, dict | list):
                value = json.dumps(value)
            sources = ", ".join(sorted({s["via"] for s in claim["sources"]}))
            prefix = f"{label}:" if i == 0 else ""
            print(f"  {prefix:<34} {str(value)[:90]}  [{claim['confidence']:.2f} {sources}]")
        if multi and len(claims) > 5:
            print(f"  {'':<34} ... {len(claims) - 5} more")
        if not multi and len(claims) > 1:
            print(f"  {'':<34} also reported: {', '.join(str(c['value'])[:40] for c in claims[1:4])}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="company-research", description="Public-data company profiles for moneyfinder.")
    commands = parser.add_subparsers(required=True)

    run = commands.add_parser("run", help="research a company domain and write its profile")
    run.add_argument("domain", help="company domain, e.g. joespizza.com")
    run.add_argument("--business-id", help="moneyfinder business id to record in the profile")
    run.add_argument("--email", help="contact email to record (its domain is compared to the company's)")
    run.add_argument("--out", help=f"output folder (default: {config.DATA_DIR}/<domain>)")
    run.add_argument("--only", help=f"comma-separated collectors: {','.join(pipeline.COLLECTORS)}")
    run.add_argument("--no-llm", action="store_true", help="skip the optional Bedrock synthesis")
    run.set_defaults(func=cmd_run)

    show = commands.add_parser("show", help="print a stored profile")
    show.add_argument("domain")
    show.add_argument("--out", help="folder the profile was written to")
    show.add_argument("--json", action="store_true", help="print the full profile JSON")
    show.set_defaults(func=cmd_show)

    check = commands.add_parser("check", help="validate and normalize a domain (no network)")
    check.add_argument("domain")
    check.set_defaults(func=cmd_check)

    commands.add_parser("keys", help="show which API keys are configured (never prints values)").set_defaults(func=cmd_keys)

    args = parser.parse_args(argv)
    try:
        args.func(args)
    except (domain.InvalidDomain, FileNotFoundError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
