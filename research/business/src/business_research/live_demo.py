"""One live run for the demo page (/live): demo email -> Gmail -> email agent and web research agents in parallel ->
dossier in SurrealDB -> Anchor browser fill -> the credit forms with the data that goes on them.

Only the synthetic demo business is wired. Its mailbox and its web research are stored fixtures (the page says so);
the Claude pass over the mail, the dossier build, the SurrealDB push and the browser fill run live.
"""

import json
import os
import re
import subprocess
import threading
import time
import uuid
from collections import Counter

from . import demo, email_facts, kb_sync
from .dossier import mask_ein

REPO_DIR = kb_sync.REPO_DIR
DEMO_EMAILS = {"marisol@gowanuskettle.example": REPO_DIR / "demo" / "gowanus-kettle"}
STEPS = [
    ("gmail", "Gmail linked, reading company mail"),
    ("email", "Email agent: Claude on Bedrock reads the mail"),
    ("web", "Web research agents"),
    ("kb", "Dossier stored in SurrealDB"),
    ("browser", "Agentic browser (Anchor) fills NY Form IT-636 (official PDF)"),
    ("forms", "Forms ready"),
]
COLLECTORS = {
    "website": "Website crawl (Firecrawl)",
    "nys_dos": "NY Department of State registry",
    "nyc_open_data": "NYC Open Data",
    "firmographics": "Firmographics (Firecrawl Alexandria)",
    "news": "News and web search",
    "bbb": "Better Business Bureau",
    "linkedin": "LinkedIn",
    "llm": "Profile summary (Claude on Bedrock)",
    "nys_unclaimed": "NY unclaimed funds search (State Comptroller)",
}
FORM_DATA = [
    ("legal_name", "Legal name"), ("ein", "EIN"), ("hq_address", "Address"), ("entity_type", "Entity type"),
    ("naics", "NAICS"), ("employees", "Employees"), ("officer_name", "Officer"), ("officer_title", "Title"),
    ("tax_year", "Tax year"), ("ny_beer_barrels", "Beer brewed in NY (barrels)"),
    ("sla_license_number", "SLA license number"),
]
FILL_HOLD_S = 20

_jobs: dict[str, dict] = {}
_lock = threading.Lock()


def start(email: str) -> str:
    email = (email or "").strip().lower()
    fixture = DEMO_EMAILS.get(email)
    if not fixture:
        raise ValueError(f"Use the demo email {', '.join(DEMO_EMAILS)}")
    job = {
        "id": uuid.uuid4().hex[:12], "email": email, "started": time.time(), "done": False, "error": None,
        "steps": [{"id": k, "label": label, "state": "pending"} for k, label in STEPS],
        "log": [], "pdf": None, "live_view": None, "screenshot": None, "fill": None, "forms": None, "data": None,
    }
    with _lock:
        _jobs[job["id"]] = job
    threading.Thread(target=_run, args=(job, fixture), daemon=True).start()
    return job["id"]


def get(job_id: str) -> dict | None:
    with _lock:
        job = _jobs.get(job_id)
        return json.loads(json.dumps(job, default=str)) if job else None


def _log(job: dict, step: str, text: str) -> None:
    with _lock:
        job["log"].append({"t": round(time.time() - job["started"], 1), "step": step, "text": text})


def _step(job: dict, step: str, state: str) -> None:
    with _lock:
        next(s for s in job["steps"] if s["id"] == step)["state"] = state


def _run(job: dict, fixture) -> None:
    try:
        _flow(job, fixture)
    except Exception as e:  # shown on the page; the run just stops
        job["error"] = f"{type(e).__name__}: {e}"
        _log(job, "error", job["error"])
    finally:
        job["done"] = True


def _flow(job: dict, fixture) -> None:
    business = json.loads((fixture / "business.json").read_text())
    profile = json.loads((fixture / "profile.json").read_text())
    messages = [json.loads(line) for line in (fixture / "inbox.jsonl").read_text().splitlines() if line.strip()]

    _step(job, "gmail", "running")
    _log(job, "gmail", f"Gmail linked for {job['email']}, read-only (synthetic demo mailbox)")
    for m in messages[:8]:
        _log(job, "gmail", f"reading: {m.get('subject')} ({m.get('sender_domain')})")
        time.sleep(0.15)
    _log(job, "gmail", f"{len(messages)} messages read for {business.get('name')}")
    _step(job, "gmail", "done")

    agents = [
        threading.Thread(target=_guarded, args=(job, "email", _email_agent, messages)),
        threading.Thread(target=_guarded, args=(job, "web", _web_research, profile)),
    ]
    for t in agents:
        t.start()
    for t in agents:
        t.join()

    _step(job, "kb", "running")
    result, paths = demo.seed(fixture, use_llm=True)
    facts, credits = result.get("facts") or [], result.get("credits") or []
    kinds = Counter(f.get("source_kind") for f in facts)
    _log(job, "kb", f"Dossier built: {len(facts)} facts ({', '.join(f'{n} {k}' for k, n in kinds.most_common())}), "
                    f"{len(credits)} matched credits, missing info: {', '.join(result.get('missing_info') or []) or 'none'}")
    pushed = kb_sync.enabled() and kb_sync.push(paths[-1])
    if pushed:
        _log(job, "kb", f"Stored as business:{result.get('slug')} in SurrealDB Cloud (ns moneyfinder, db main)")
    else:
        _log(job, "kb", "SurrealDB push failed or isn't configured; the browser reads the dossier file instead")
    _step(job, "kb", "done" if pushed else "failed")
    with _lock:
        job["forms"], job["data"] = _forms(result)

    _browser(job, result.get("slug"))


def _guarded(job: dict, step: str, fn, arg) -> None:
    _step(job, step, "running")
    try:
        fn(job, arg)
        _step(job, step, "done")
    except Exception as e:  # one agent failing doesn't stop the other
        _log(job, step, f"failed: {type(e).__name__}: {str(e)[:200]}")
        _step(job, step, "failed")


def _email_agent(job: dict, messages: list[dict]) -> None:
    subjects = {m.get("id"): m.get("subject") for m in messages}
    rules = email_facts.deterministic(messages)
    _log(job, "email", f"Rules pass: {len(rules)} facts from senders, agencies and patterns")
    for f in rules[:6]:
        _log(job, "email", _fact_line(f, subjects))
    _log(job, "email", "Claude on Bedrock is reading the relevant messages...")
    found = email_facts.llm_facts(messages)
    _log(job, "email", f"Claude returned {len(found)} facts, each grounded in the message it quotes")
    for f in found:
        _log(job, "email", _fact_line(f, subjects))


def _web_research(job: dict, profile: dict) -> None:
    fields = profile.get("fields") or {}
    names = list(profile.get("collectors") or {})
    _log(job, "web", f"{len(names)} research agents on {profile.get('domain')} "
                     "(synthetic business: replaying its stored research results)")
    for name in names:
        _log(job, "web", f"{COLLECTORS.get(name, name)}: started")
    for name in names:
        time.sleep(1.8)
        found = [(k, claims[0].get("value")) for k, claims in fields.items()
                 if claims and name in (claims[0].get("collectors") or [])]
        summary = ", ".join(f"{k} = {_short(v)}" for k, v in found[:4]) or "nothing new"
        _log(job, "web", f"{COLLECTORS.get(name, name)}: {summary}")


def _browser(job: dict, slug: str) -> None:
    _step(job, "browser", "running")
    cmd = ["uv", "run", "--project", str(REPO_DIR / "kb"), "--with", "playwright", "python",
           str(REPO_DIR / "form-filling" / "fill_pdf.py"), "--slug", slug, "--hold", str(FILL_HOLD_S), "--watch-delay", "4"]
    # fill.py also opens the live view in its own browser tab, in case the embedded frame doesn't render it
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}  # uv would warn about the app's venv
    proc = subprocess.Popen(cmd, cwd=REPO_DIR, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            bufsize=1)
    receipt = None
    for raw in proc.stdout:
        line = re.sub(r"^\[\s*[\d.]+s\]\s*", "", raw.strip())
        if not line:
            continue
        if m := re.search(r"LIVE VIEW:\s*(\S+)", line):
            with _lock:
                job["live_view"] = m.group(1)
            _log(job, "browser", "Anchor cloud browser started: the live view opens in a new tab and below")
            continue
        if "rt=" in line or "live_view" in line:
            continue  # the live-view link carries an access token
        if m := re.search(r"screenshot (\S+\.png)", line):
            with _lock:
                job["screenshot"] = str(REPO_DIR / m.group(1))
        if m := re.search(r"filled pdf (\S+\.pdf)", line):
            with _lock:
                job["pdf"] = str(REPO_DIR / m.group(1))
        if m := re.search(r"receipt (\S+\.json)", line):
            receipt = REPO_DIR / m.group(1)
        _log(job, "browser", line)
        if line.startswith("NOT submitted") and receipt and receipt.exists():
            fill = json.loads(receipt.read_text())
            with _lock:
                job["fill"] = {"filled": fill.get("filled"), "needs_user": fill.get("needs_user"),
                               "status": fill.get("status")}
            _step(job, "forms", "done")
            _log(job, "forms", f"{len(job['forms'] or [])} credits with official forms ready, data attached below")
    proc.wait(timeout=60)
    _step(job, "browser", "done" if proc.returncode == 0 else "failed")
    if proc.returncode != 0:
        _step(job, "forms", "done")


def _forms(result: dict) -> tuple[list[dict], list[dict]]:
    business, facts = result.get("business") or {}, result.get("facts") or []
    data = []
    for key, label in FORM_DATA:
        best = business.get(key)
        fact = next((f for f in facts if f.get("key") == key and _same(f.get("value"), best)), None) if best else \
            next((f for f in facts if f.get("key") == key and f.get("value") not in (None, "")), None)
        value = best if best not in (None, "", []) else (fact or {}).get("value")
        if isinstance(value, list):
            value = value[0] if value else None
        source = (fact or {}).get("source_kind", "")
        data.append({"label": label, "value": mask_ein(value) if key == "ein" and value else (value or "ask the user"),
                     "source": source})
    open_credits = [c for c in result.get("credits") or [] if c.get("forms") and c.get("status") != "expired"]
    chosen = [c for c in open_credits if c.get("tier") == "niche"] or open_credits[:8]
    forms = [{"name": c.get("name"), "jurisdiction": c.get("jurisdiction"), "why": _short((c.get("why") or [""])[0], 110),
              "forms": [{"code": f.get("code"), "title": f.get("label") or f.get("title"), "url": f.get("url")}
                        for f in c.get("forms") or []]}
             for c in chosen]
    return forms, data


def _same(fact_value, best) -> bool:
    if isinstance(best, list):
        return fact_value in best or (isinstance(fact_value, dict) and fact_value.get("code") in best)
    return fact_value == best


def _fact_line(fact: dict, subjects: dict) -> str:
    value = mask_ein(fact.get("value")) if fact.get("key") == "ein" else _short(fact.get("value"))
    subject = subjects.get(fact.get("message_id"))
    return f"{fact.get('key')} = {value}" + (f'  (from "{subject}")' if subject else "")


def _short(value, width: int = 60) -> str:
    text = ", ".join(map(str, value)) if isinstance(value, list) else str(value)
    return text if len(text) <= width else text[: width - 1] + "…"
