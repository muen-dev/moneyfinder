"""Command line entry point: `uv run business-research <command>`."""

import argparse
import json
import sys
from pathlib import Path
from collections.abc import Iterable, Iterator

from googleapiclient.errors import HttpError

from . import store
from .gmail import auth
from .gmail.client import DEFAULT_QUERY, GmailClient
from .gmail.parse import EmailMessage


def cmd_serve(args: argparse.Namespace) -> None:
    from .web.app import create_app  # Flask is only needed for the server

    print(f"Open http://localhost:{args.port}")
    print(f"OAuth redirect URI (must be registered on the client): http://localhost:{args.port}/oauth/callback")
    create_app(args.port).run(host="127.0.0.1", port=args.port)


def cmd_list(args: argparse.Namespace) -> None:
    connections = auth.list_connections()
    if not connections:
        print("No businesses connected.")
    for conn in connections:
        print(f"{conn.business_id}\t{conn.email}\tconnected {conn.connected_at}")


def cmd_fetch(args: argparse.Namespace) -> None:
    conn = auth.load(args.business_id)
    # Always under DATA_DIR, which is git-ignored, so real mail can't land somewhere committable.
    out = store.messages_path(args.business_id)
    messages = GmailClient(conn.credentials).search(args.query, limit=args.limit)
    count = store.write_messages(out, _with_progress(messages))
    print(file=sys.stderr)
    print(f"Wrote {count} messages from {conn.email} to {out}")


def cmd_disconnect(args: argparse.Namespace) -> None:
    revoked = auth.disconnect(args.business_id)
    store.delete_messages(args.business_id)
    status = "access revoked" if revoked else "token deleted (Google did not confirm the revoke)"
    print(f"Disconnected {args.business_id}: {status}, fetched mail deleted")


def cmd_dossier(args: argparse.Namespace) -> None:
    from collections import Counter

    from . import dossier

    if args.business_id and not args.domain:
        result = dossier.build_for_business(args.business_id, use_llm=not args.no_llm)
    elif args.domain:
        result = dossier.build_for_domain(args.domain, business_id=args.business_id, use_llm=not args.no_llm)
    else:
        raise ValueError("give a domain or --business-id")
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        return
    b = result["business"]
    kinds = Counter(f["source_kind"] for f in result["facts"])
    print(f"{result['slug']}  {b.get('name')}  ({len(result['facts'])} facts: {dict(kinds)})")
    for key in ("legal_name", "employees", "hq_address", "founded_year", "industry", "naics", "payroll_provider"):
        print(f"  {key:<18} {b.get(key)}")
    print(f"  {'ein':<18} {dossier.mask_ein(b['ein']) if b.get('ein') else None}")
    print(f"  email: {result['email']['message_count']} messages, llm {result['email'].get('llm', '-')}")
    print(f"  credits: {len(result['credits'])}   missing: {', '.join(result['missing_info'])}")


def cmd_demo_seed(args: argparse.Namespace) -> None:
    from collections import Counter

    from . import demo

    result, paths = demo.seed(args.fixture_dir, use_llm=not args.no_llm)
    kinds = Counter(f["source_kind"] for f in result["facts"])
    with_forms = [c for c in result["credits"] if c.get("forms")]
    print(f"seeded demo business {result['business'].get('name')} ({result['domain']}, slug {result['slug']})")
    print(f"  facts: {len(result['facts'])} {dict(kinds)}; email: {result['email']['message_count']} messages, llm {result['email'].get('llm')}")
    print(f"  credits: {len(result['credits'])} ({len(with_forms)} with PDF forms); missing: {', '.join(result['missing_info']) or 'none'}")
    for path in paths:
        print(f"  wrote {path}")


def _with_progress(messages: Iterable[EmailMessage]) -> Iterator[EmailMessage]:
    for count, message in enumerate(messages, 1):
        print(f"\rfetched {count}", end="", file=sys.stderr)
        yield message


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="business-research", description="Gather business context for moneyfinder.")
    commands = parser.add_subparsers(required=True)

    serve = commands.add_parser("serve", help="run the local dev server to connect businesses with Google sign-in")
    serve.add_argument("--port", type=int, default=8000)
    serve.set_defaults(func=cmd_serve)

    commands.add_parser("list", help="show connected businesses").set_defaults(func=cmd_list)

    fetch = commands.add_parser("fetch", help="download matching messages to JSONL")
    fetch.add_argument("business_id", help="id shown by `list`")
    fetch.add_argument("-q", "--query", default=DEFAULT_QUERY, help=f"Gmail search query (default: {DEFAULT_QUERY!r})")
    fetch.add_argument("-n", "--limit", type=int, default=200, help="max messages (default: 200)")
    fetch.set_defaults(func=cmd_fetch)

    disconnect = commands.add_parser("disconnect", help="revoke access and delete the token and fetched mail")
    disconnect.add_argument("business_id")
    disconnect.set_defaults(func=cmd_disconnect)

    build = commands.add_parser("dossier", help="build the form-ready dossier.json for a domain or connected business")
    build.add_argument("domain", nargs="?", help="company domain with a stored profile (research/company/data)")
    build.add_argument("--business-id", help="connected business id (adds its fetched mail and signup answers)")
    build.add_argument("--no-llm", action="store_true", help="skip the Bedrock pass over mail")
    build.add_argument("--json", action="store_true", help="print the dossier JSON (EIN unmasked)")
    build.set_defaults(func=cmd_dossier)

    seed = commands.add_parser("demo-seed", help="load a synthetic demo business (repo-root demo/<name>/) and build its dossier")
    seed.add_argument("fixture_dir", type=Path, help="e.g. ../../demo/gowanus-kettle")
    seed.add_argument("--no-llm", action="store_true", help="skip the Bedrock pass over the synthetic mail")
    seed.set_defaults(func=cmd_demo_seed)

    args = parser.parse_args(argv)
    try:
        args.func(args)
    except (auth.NotConnectedError, FileNotFoundError, ValueError, HttpError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
