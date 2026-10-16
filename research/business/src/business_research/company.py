"""A business's company domain and its background public-data research (research/company).

Everything lives under DATA_DIR/<id>/ (git-ignored, owner-only), so disconnecting removes it:
  business.json   the company domain the owner entered
  research.json   research status: queued | running | done | failed
  company/        profile.json plus raw API responses
"""

import json
import os
import shutil
import threading
from datetime import UTC, datetime
from pathlib import Path

from company_research import pipeline
from company_research import store as company_store
from company_research.domain import InvalidDomain, from_email, is_free_email_domain, normalize

from . import config, ids

# Replaced in tests so no research (or network call) actually runs.
research_fn = pipeline.research

_lock = threading.Lock()
_active: set[str] = set()  # business ids with research running in this process


def business_dir(business_id: str) -> Path:
    return config.DATA_DIR / ids.check(business_id)


def research_dir(business_id: str) -> Path:
    return business_dir(business_id) / "company"


def validate_domain(raw: str) -> str:
    """Normalized company domain, or InvalidDomain with a message for the form."""
    domain = normalize(raw)
    if is_free_email_domain(domain):
        raise InvalidDomain(f"{domain} is an email provider, not your company's website. Enter your own domain.")
    return domain


def suggested_domain(email: str) -> str:
    """Prefill for the domain form: the email's domain unless it's a personal mailbox provider."""
    return from_email(email) or ""


def get_domain(business_id: str) -> str | None:
    return _read(business_dir(business_id) / "business.json").get("domain")


def set_domain(business_id: str, raw: str) -> str:
    domain = validate_domain(raw)
    _write(business_dir(business_id) / "business.json", {"domain": domain, "updated_at": _now()})
    return domain


def status(business_id: str) -> dict | None:
    state = _read(business_dir(business_id) / "research.json") or None
    if state and state.get("status") in ("queued", "running") and business_id not in _active:
        return state | {"status": "failed", "error": "Interrupted because the server restarted. Run it again."}
    return state


def profile(business_id: str) -> dict | None:
    try:
        return company_store.read_profile(research_dir(business_id))
    except (OSError, ValueError):
        return None


def start(business_id: str, domain: str, email: str) -> bool:
    """Queue research in a background thread. False if one is already running for this business."""
    with _lock:
        if business_id in _active:
            return False
        _active.add(business_id)
    _write(business_dir(business_id) / "research.json", {"status": "queued", "domain": domain, "queued_at": _now()})
    _spawn(_run, business_id, domain, email)
    return True


def _spawn(target, *args) -> None:
    threading.Thread(target=target, args=args, daemon=True, name=f"research-{args[0]}").start()


def _run(business_id: str, domain: str, email: str) -> None:
    path = business_dir(business_id) / "research.json"
    state = {"status": "running", "domain": domain, "started_at": _now()}
    try:
        _write(path, state)
        research_fn(domain, business_id=business_id, contact_email=email, out_dir=research_dir(business_id))
        state |= {"status": "done", "finished_at": _now()}
    except Exception as e:  # shown on the business page; the run itself is fail-soft per source
        state |= {"status": "failed", "finished_at": _now(), "error": str(e)[:300] or type(e).__name__}
    finally:
        with _lock:
            _active.discard(business_id)
    if _connected(business_id):
        _write(path, state)
    else:
        # Disconnected while this ran: don't leave its output behind.
        shutil.rmtree(business_dir(business_id), ignore_errors=True)


def _connected(business_id: str) -> bool:
    return (config.TOKEN_DIR / f"{ids.check(business_id)}.json").exists()


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _read(path: Path) -> dict:
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".partial")
    fd = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(partial, path)
    finally:
        partial.unlink(missing_ok=True)
