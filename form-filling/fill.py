"""Agentic browser form filler: fill the mock claim portal from a business dossier in an Anchor cloud browser.

Loads the dossier (SurrealDB Cloud, falling back to research/company/data/<domain>/dossier.json), maps it
to the mock portal's fields, types the approved values in an Anchor Browser session you can watch live,
reads the DOM back and diffs it, screenshots, writes a JSON receipt and stops before submit.

    uv run --project kb --with playwright python form-filling/fill.py --slug gowanuskettle-example
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from dotenv import dotenv_values

REPO = Path(__file__).resolve().parents[1]
PORTAL = REPO / "mock_portal" / "index.html"
OUT = Path(__file__).resolve().parent / "out"
ANCHOR = "https://api.anchorbrowser.io/v1/sessions"

# Portal fields in page order. Fields with no dossier source are left blank for the user.
PORTAL_FIELDS = [
    "legal_name", "authorized_representative", "role", "city", "zip",
    "property_name", "amount_requested", "pay_to",
]
SOURCE_RANK = {"user": 0, "registry": 1, "enrichment": 2, "web": 3, "email": 4, "llm": 5}
START = time.monotonic()


def log(msg: str) -> None:
    print(f"[{time.monotonic() - START:5.1f}s] {msg}", flush=True)


def mask_ein(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    return f"**-***{digits[-4:]}" if len(digits) == 9 else value


def masked(value: str) -> str:
    """Mask anything shaped like an EIN before it reaches logs or the receipt."""
    return re.sub(r"\b\d{2}-?\d{7}\b", lambda m: mask_ein(m.group()), value)


# --- dossier -------------------------------------------------------------------------------------

def dossier_from_surreal(slug: str) -> dict[str, Any] | None:
    sys.path.insert(0, str(REPO / "kb" / "src"))
    from moneyfinder_kb.config import Settings
    from moneyfinder_kb.db import DB

    db = DB(Settings.from_env())
    try:
        full = db.one("RETURN type::record('business', $slug).dossier;", {"slug": slug})
        if isinstance(full, dict) and full.get("business"):
            return full
        brief = db.one("RETURN fn::business_dossier($slug);", {"slug": slug})
        return brief if isinstance(brief, dict) and brief.get("business") else None
    finally:
        db.close()


def dossier_from_file(slug: str, domain: str | None) -> dict[str, Any] | None:
    candidates = [REPO / "research" / "company" / "data" / domain / "dossier.json"] if domain else []
    candidates += sorted(REPO.glob("research/*/data/*/dossier.json"))
    for path in candidates:
        if path.is_file():
            d = json.loads(path.read_text())
            if d.get("slug") == slug or (domain and d.get("domain") == domain):
                return d
    return None


def load_dossier(slug: str, domain: str | None) -> tuple[dict[str, Any], str]:
    try:
        d = dossier_from_surreal(slug)
        if d:
            return d, "surrealdb"
        log(f"SurrealDB has no dossier for {slug}; using the file")
    except Exception as e:  # noqa: BLE001 - any DB failure falls back to the file
        log(f"SurrealDB unavailable ({type(e).__name__}: {str(e)[:120]}); using the file")
    d = dossier_from_file(slug, domain)
    if not d:
        raise SystemExit(f"no dossier for slug {slug!r} in SurrealDB or research/*/data/")
    return d, "file"


def claim_from_api(api_url: str, claim_id: str) -> dict[str, Any]:
    """Load the user's selected claim, including its provider-backed match."""
    url = f"{api_url.rstrip('/')}/api/claims/{claim_id}"
    try:
        response = httpx.get(url, timeout=15)
        response.raise_for_status()
        bundle = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise SystemExit(f"could not load claim {claim_id!r} from {url}: {exc}") from exc
    if not isinstance(bundle, dict) or not isinstance(bundle.get("claim"), dict):
        raise SystemExit(f"claim endpoint returned an invalid bundle for {claim_id!r}")
    return bundle


def dossier_for_claim(bundle: dict[str, Any], fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    """Overlay the selected search hit onto a dossier without changing provenance."""
    claim = bundle["claim"]
    profile = claim.get("profile") or {}
    dossier = json.loads(json.dumps(fallback)) if fallback else {
        "schema_version": 1,
        "slug": claim.get("business_id") or claim.get("id"),
        "business": {},
        "facts": [],
    }
    business = dossier.setdefault("business", {})
    legal_name = profile.get("legal_name") or claim.get("business_name")
    if legal_name:
        business["legal_name"] = legal_name
    representative = profile.get("authorized_representative") or {}
    if representative.get("name"):
        business["officer_name"] = representative["name"]
    if representative.get("role"):
        business["officer_title"] = representative["role"]
    addresses = profile.get("addresses") or []
    if addresses and not business.get("hq_address"):
        address = addresses[0]
        parts = [address.get("street"), address.get("city"), address.get("state"), address.get("zip")]
        business["hq_address"] = ", ".join(str(part) for part in parts if part)

    hit = claim.get("hit") or {}
    source = str(hit.get("source") or "claim_search")
    facts = dossier.setdefault("facts", [])
    facts = [fact for fact in facts if fact.get("key") not in {"unclaimed_found_name", "unclaimed_amount"}]
    if hit.get("found_name"):
        facts.append({
            "key": "unclaimed_found_name",
            "value": hit["found_name"],
            "source": source,
            "source_kind": "provider",
            "confidence": hit.get("confidence"),
        })
    amount_cents = hit.get("amount_cents")
    if amount_cents is not None:
        facts.append({
            "key": "unclaimed_amount",
            "value": f"{int(amount_cents) / 100:.2f}",
            "source": source,
            "source_kind": "provider",
            "confidence": hit.get("confidence"),
        })
    dossier["facts"] = facts
    dossier["claim_id"] = claim.get("id")
    dossier["claim_source"] = source
    return dossier


def source_of(dossier: dict[str, Any], key: str, value: Any) -> str:
    """Best provenance for a business value, using the dossier's precedence (user > registry > ...)."""
    facts = [f for f in dossier.get("facts") or [] if f.get("key") == key and f.get("value") == value]
    if not facts:
        return "dossier"
    best = min(facts, key=lambda f: (SOURCE_RANK.get(f.get("source_kind"), 9), -(f.get("confidence") or 0)))
    return best.get("source_kind") or "dossier"


def load_runtime_dossier(
    slug: str, domain: str | None, claim_id: str | None, api_url: str
) -> tuple[dict[str, Any], str]:
    """Prefer the selected claim while retaining any existing business dossier."""
    bundle = claim_from_api(api_url, claim_id) if claim_id else None
    try:
        dossier, origin = load_dossier(slug, domain)
    except SystemExit:
        if not bundle:
            raise
        return dossier_for_claim(bundle), f"api_claim:{claim_id}"
    if bundle:
        return dossier_for_claim(bundle, dossier), f"{origin}+claim:{claim_id}"
    return dossier, origin


def parse_address(addr: str) -> dict[str, str]:
    """'417 Sackett Street, Brooklyn, NY 11231' -> city, state, zip. Missing parts stay missing."""
    out: dict[str, str] = {}
    parts = [p.strip() for p in (addr or "").split(",") if p.strip()]
    m = re.search(r"\b([A-Z]{2})\s+(\d{5})(?:-\d{4})?\s*$", addr or "")
    if m:
        out["state"], out["zip"] = m.group(1), m.group(2)
        if len(parts) >= 3:
            out["city"] = parts[-2]
    return out


def fact_value(dossier: dict[str, Any], key: str) -> tuple[Any, str, str]:
    """(value, key, source kind) of the first fact with this key, for values outside the business block."""
    for f in dossier.get("facts") or []:
        if f.get("key") == key and f.get("value") not in (None, ""):
            return f.get("value"), key, f.get("source_kind") or ""
    return None, key, ""


def plan_fields(dossier: dict[str, Any]) -> tuple[dict[str, dict[str, str]], list[dict[str, str]]]:
    """Approved values per portal field (value + source) and the fields that need the user."""
    b = dossier.get("business") or {}
    addr = parse_address(b.get("hq_address") or "")
    addr_src = source_of(dossier, "hq_address", b.get("hq_address"))
    candidates: dict[str, tuple[Any, str, str]] = {
        "legal_name": (b.get("legal_name"), "legal_name", source_of(dossier, "legal_name", b.get("legal_name"))),
        "authorized_representative": (b.get("officer_name"), "officer_name",
                                      source_of(dossier, "officer_name", b.get("officer_name"))),
        "role": (b.get("officer_title"), "officer_title", source_of(dossier, "officer_title", b.get("officer_title"))),
        "city": (addr.get("city"), "hq_address", addr_src),
        "zip": (addr.get("zip"), "hq_address", addr_src),
        "pay_to": (b.get("legal_name"), "legal_name", source_of(dossier, "legal_name", b.get("legal_name"))),
        # From the business's unclaimed-funds record (research fact); blank when there is none, never guessed.
        "property_name": (*fact_value(dossier, "unclaimed_found_name"),),
        "amount_requested": (*fact_value(dossier, "unclaimed_amount"),),
    }
    approved, needs_user = {}, []
    for name in PORTAL_FIELDS:
        value, key, src = candidates[name]
        if value in (None, ""):
            needs_user.append({"field": name, "reason": f"no source value ({key})"})
        else:
            approved[name] = {"value": str(value), "from": f"{'facts' if key.startswith('unclaimed_') else 'business'}.{key}",
                              "source": src}
    return approved, needs_user


# --- Anchor --------------------------------------------------------------------------------------

def anchor_key() -> str:
    key = os.environ.get("ANCHOR_API_KEY") or dotenv_values(REPO / ".env").get("ANCHOR_API_KEY")
    if not key:
        raise SystemExit("ANCHOR_API_KEY is not set in the repo-root .env")
    return key.strip()


def create_session(key: str) -> dict[str, Any]:
    # Lean session: no recording, no proxy, short timeouts. Headful so the live view works.
    body = {
        "session": {"recording": {"active": False}, "proxy": {"active": False},
                    "timeout": {"max_duration": 5, "idle_timeout": 2}},
        "browser": {"headless": {"active": False}},
    }
    headers = {"anchor-api-key": key, "Content-Type": "application/json"}
    r = httpx.post(ANCHOR, json=body, headers=headers, timeout=60)
    if r.status_code == 400:  # an option this account/API version rejects: fall back to defaults
        r = httpx.post(ANCHOR, json={}, headers=headers, timeout=60)
    if r.status_code >= 400:
        raise SystemExit(f"Anchor session create failed: HTTP {r.status_code} {r.text[:300]}")
    data = r.json().get("data") or r.json()
    if not data.get("cdp_url"):
        raise SystemExit(f"Anchor response has no cdp_url (keys: {sorted(data)})")
    return data


def end_session(key: str, session_id: str) -> None:
    try:
        r = httpx.delete(f"{ANCHOR}/{session_id}", headers={"anchor-api-key": key}, timeout=30)
        log(f"Anchor session {session_id} ended (HTTP {r.status_code})")
    except Exception as e:  # noqa: BLE001
        log(f"WARNING: could not end Anchor session {session_id}: {e}")


# --- browser -------------------------------------------------------------------------------------

HIGHLIGHT = """el => { el.scrollIntoView({block: 'center'});
  el.style.outline = '3px solid #FFB000'; el.style.outlineOffset = '2px';
  el.style.transition = 'background-color .3s'; el.style.backgroundColor = '#FFF8E1'; }"""
DONE = """el => { el.style.outline = '2px solid #2BA84A'; el.style.backgroundColor = '#E9F7EE'; }"""
# One CDP round trip per field: highlight, clear, type char by char (input events per char), mark done.
# Per-keystroke CDP calls to a cloud browser cost ~70 ms each, so typing in-page is much faster to watch.
TYPE_IN_PAGE = """async (el, [text, delay]) => {
  el.scrollIntoView({block: 'center'}); el.focus();
  el.style.outline = '3px solid #FFB000'; el.style.outlineOffset = '2px'; el.style.backgroundColor = '#FFF8E1';
  el.value = ''; el.dispatchEvent(new Event('input', {bubbles: true}));
  for (const ch of text) {
    el.value += ch; el.dispatchEvent(new Event('input', {bubbles: true}));
    await new Promise(r => setTimeout(r, delay));
  }
  el.dispatchEvent(new Event('change', {bubbles: true}));
  el.style.outline = '2px solid #2BA84A'; el.style.backgroundColor = '#E9F7EE';
  return el.value;
}"""
NEEDS_USER = """el => { el.style.outline = '2px dashed #E8553F'; el.placeholder = 'Needs your input'; }"""


def fill_portal(page, approved: dict[str, dict[str, str]], needs_user: list[dict[str, str]],
                type_delay: int, real_keys: bool = False) -> tuple[list[dict[str, Any]], list[str]]:
    skipped: list[str] = []
    # One round trip: which fields the portal has, and which it marks requires_confirmation.
    confirm_only = page.evaluate(
        "() => Object.fromEntries([...document.querySelectorAll('input[data-field]')].map(e => [e.dataset.field,"
        " e.hasAttribute('data-requires-confirmation') || e.dataset.requiresConfirmation === 'true'"
        " || e.classList.contains('requires_confirmation')]))")
    for name in PORTAL_FIELDS:
        if name not in confirm_only:
            continue
        loc = page.locator(f'input[data-field="{name}"]')
        if name not in approved:
            loc.evaluate(NEEDS_USER)
            continue
        if confirm_only[name]:
            skipped.append(name)
            log(f"skipping {name}: portal marks it requires_confirmation")
            continue
        a = approved[name]
        log(f"filling {name} <- {masked(a['value'])} (source: {a['source']}, {a['from']})")
        if real_keys:  # real CDP keystrokes: slower over the network, closest to a human
            loc.evaluate(HIGHLIGHT)
            loc.click()
            loc.fill("")  # clear any pre-filled value (zip ships with a flagged 11202)
            loc.press_sequentially(a["value"], delay=type_delay)
            loc.evaluate(DONE)
        else:  # clears the pre-filled value too
            loc.evaluate(TYPE_IN_PAGE, [a["value"], type_delay])
    for name in skipped:
        approved.pop(name, None)
        needs_user.append({"field": name, "reason": "portal requires_confirmation"})

    # Read every field back and diff against what was approved (blank for needs_user fields).
    dom = page.evaluate("() => Object.fromEntries([...document.querySelectorAll('input[data-field]')]"
                        ".map(e => [e.dataset.field, e.value]))")
    mismatches = []
    for name in PORTAL_FIELDS:
        expected = approved[name]["value"] if name in approved else ""
        if name in skipped:
            continue
        got = dom.get(name)
        if got != expected:
            mismatches.append({"field": name, "expected": masked(expected), "dom": masked(got or "")})
    return mismatches, skipped


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--slug", default="gowanuskettle-example")
    ap.add_argument("--domain", help="dossier file fallback domain (default: slug with the last '-' as '.')")
    ap.add_argument("--claim-id", help="load the selected claim from the local API")
    ap.add_argument("--api-url", default=os.environ.get("MONEYFINDER_API_URL", "http://127.0.0.1:4173"),
                    help="MoneyFinder API base URL used with --claim-id")
    ap.add_argument("--hold", type=float, default=10, help="seconds to keep the session open for recording")
    ap.add_argument("--watch-delay", type=float, default=2.5, help="seconds for the live view to load before typing")
    ap.add_argument("--type-delay", type=int, default=20, help="ms per typed character")
    ap.add_argument("--no-open", action="store_true", help="don't open the live view in the local browser")
    ap.add_argument("--real-keys", action="store_true", help="type with CDP key events (slower) instead of in-page")
    args = ap.parse_args()
    domain = args.domain or (args.slug.rsplit("-", 1)[0] + "." + args.slug.rsplit("-", 1)[1]
                             if "-" in args.slug else args.slug)

    key = anchor_key()
    log(f"starting: slug={args.slug}; creating Anchor session and loading dossier in parallel")
    with ThreadPoolExecutor(2) as pool:
        session_f = pool.submit(create_session, key)
        dossier_f = pool.submit(load_runtime_dossier, args.slug, domain, args.claim_id, args.api_url)
        session = session_f.result()
        sid, live = session.get("id"), session.get("live_view_url")
        log(f"Anchor session {sid}")
        print(f"\n  LIVE VIEW: {live}\n", flush=True)
        if live and not args.no_open:
            subprocess.run(["open", live], check=False)
        try:
            dossier, origin = dossier_f.result()
        except BaseException:
            end_session(key, sid)
            raise

    receipt: dict[str, Any] = {}
    try:
        b = dossier.get("business") or {}
        log(f"dossier for {b.get('legal_name') or args.slug} from {origin}")
        approved, needs_user = plan_fields(dossier)

        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.connect_over_cdp(session["cdp_url"])
            ctx = browser.contexts[0] if browser.contexts else browser.new_context()
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            # Only the mock portal is ever loaded (the cloud browser can't reach localhost): no navigation.
            page.set_content(PORTAL.read_text(), wait_until="domcontentloaded")
            log(f"mock portal loaded; waiting {args.watch_delay:g}s for the live view")
            time.sleep(args.watch_delay)

            mismatches, skipped = fill_portal(page, approved, needs_user, args.type_delay, args.real_keys)

            OUT.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            shot = OUT / f"{args.slug}-{stamp}.png"
            page.screenshot(path=str(shot), full_page=True)
            log(f"screenshot {shot.relative_to(REPO)}")

            receipt = {
                "schema": "moneyfinder.form_fill_receipt/v1",
                "slug": args.slug,
                "portal": "mock_portal/index.html (mock NY unclaimed funds claim)",
                "dossier_source": origin,
                "status": "browser_mismatch" if mismatches else "ready_for_user_approval",
                "submitted": False,
                "filled": {k: {**v, "value": masked(v["value"])} for k, v in approved.items()},
                "needs_user": needs_user,
                "requires_confirmation_skipped": skipped,
                "mismatches": mismatches,
                "ein": mask_ein(str(b["ein"])) if b.get("ein") else None,
                "anchor_session_id": sid,
                "live_view_url": live,
                "screenshot": str(shot.relative_to(REPO)),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            rpath = shot.with_suffix(".json")
            rpath.write_text(json.dumps(receipt, indent=2) + "\n")
            log(f"receipt {rpath.relative_to(REPO)}")

            print()
            if mismatches:
                log("STOPPED: DOM readback does not match the approved values:")
                for m in mismatches:
                    print(f"    {m['field']}: expected {m['expected']!r}, page has {m['dom']!r}")
            else:
                log(f"readback clean: {len(approved)} fields filled and verified")
            if needs_user:
                log("needs user: " + ", ".join(f"{n['field']} ({n['reason']})" for n in needs_user))
            log("NOT submitted. Form is ready for user approval in the product UI.")
            log(f"total {time.monotonic() - START:.1f}s (before hold)")
            if args.hold > 0:
                log(f"holding the session open {args.hold:g}s for recording")
                time.sleep(args.hold)
            browser.close()
    finally:
        end_session(key, sid)
    log(f"done in {time.monotonic() - START:.1f}s")
    return 1 if receipt.get("mismatches") else 0


if __name__ == "__main__":
    sys.exit(main())
