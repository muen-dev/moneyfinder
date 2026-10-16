"""Run the collectors for one domain, merge their facts and write the profile.

The website goes first (its name, address and LinkedIn link steer the rest); the other collectors
then run concurrently. Every collector fails on its own without stopping the run.
"""

import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from concurrent.futures import TimeoutError as FuturesTimeout
from pathlib import Path

from . import config, domain as domains, store, synthesize
from .collectors import Context, bbb, linkedin, news, nyc_open_data, nys_dos, website
from .enrich import borough_from_address, naics_guess
from .profile import CollectorResult, Fact, build
from .providers import MissingKey, Providers, Recorder, now

FIRST = (website,)
THEN = (bbb, linkedin, nys_dos, nyc_open_data, news)
COLLECTORS = {c.NAME: c for c in FIRST + THEN}

_COUNTY_BOROUGH = {"new york": "Manhattan", "kings": "Brooklyn", "queens": "Queens", "bronx": "Bronx", "richmond": "Staten Island"}


def research(
    domain: str,
    *,
    business_id: str | None = None,
    contact_email: str | None = None,
    out_dir: Path | None = None,
    use_llm: bool = True,
    only: list[str] | None = None,
    providers: Providers | None = None,
    log: Callable[[str], None] = lambda message: None,
) -> dict:
    """Research a company domain and write profile.json plus raw responses. Returns the profile."""
    normalized = domains.normalize(domain)
    out_dir = out_dir or store.default_dir(normalized)
    own_providers = providers is None
    providers = providers or Providers(Recorder())
    ctx = Context(domain=normalized, providers=providers)
    selected = [c for c in FIRST + THEN if not only or c.NAME in only]
    try:
        results = _run_all([c for c in selected if c in FIRST], ctx, log)
        results += _run_all([c for c in selected if c in THEN], ctx, log)
    finally:
        if own_providers:
            providers.close()

    inputs = {"domain": normalized, "business_id": business_id, "contact_email": contact_email}
    if contact_email and "@" in contact_email:
        email_host = contact_email.rsplit("@", 1)[1].lower()
        inputs["email_domain_matches"] = email_host == normalized or email_host.endswith(f".{normalized}")
    derived = derive(results)
    profile = build(normalized, inputs, results, now(), derived)
    calls = providers.recorder.dump()

    if use_llm and synthesize.available():
        started = time.monotonic()
        llm = CollectorResult("llm")
        try:
            page_text = next((r.context.get("text", "") for r in results if r.name == "website"), "")
            llm.facts, record = synthesize.synthesize(profile, page_text)
            calls.append(record)
            log("llm: ok")
        except Exception as e:  # optional step: report it, keep the deterministic profile
            llm.status, llm.error = "failed", _short(e)
            log(f"llm: failed ({llm.error})")
        llm.duration_s = time.monotonic() - started
        results.append(llm)
        profile = build(normalized, inputs, results, profile["generated_at"], derived)
    else:
        profile["collectors"]["llm"] = {"status": "skipped", "error": "no AWS credentials" if use_llm else "disabled", "duration_s": 0, "facts": 0}

    store.write_run(out_dir, profile, calls)
    return profile


def derive(results: list[CollectorResult]) -> list[Fact]:
    """Borough from addresses and county, NAICS from industry text; each keeps its source."""
    derived = []
    for fact in (f for r in results for f in r.facts):
        if fact.field == "hq_address" and (borough := borough_from_address(str(fact.value))):
            derived.append(Fact("nyc_borough", borough, fact.source, round(fact.confidence * 0.9, 2), fact.collector, "from the address"))
        elif fact.field == "county" and (borough := _COUNTY_BOROUGH.get(str(fact.value).lower())):
            derived.append(Fact("nyc_borough", borough, fact.source, round(fact.confidence * 0.8, 2), fact.collector, "from the NY county"))
        elif fact.field in ("industry", "description") and (guess := naics_guess(str(fact.value))):
            derived.append(Fact("naics", guess, fact.source, round(fact.confidence * 0.5, 2), fact.collector, f"keyword guess from {fact.field}"))
    return derived


def _run_all(collectors, ctx: Context, log) -> list[CollectorResult]:
    if not collectors:
        return []
    pool = ThreadPoolExecutor(max_workers=len(collectors))
    futures = {pool.submit(_run_one, c, ctx, log): c for c in collectors}
    done: dict[str, CollectorResult] = {}
    try:
        for future in as_completed(futures, timeout=config.COLLECTOR_TIMEOUT):
            result = future.result()
            done[result.name] = result
    except FuturesTimeout:
        for future, collector in futures.items():
            if collector.NAME not in done:
                done[collector.NAME] = CollectorResult(collector.NAME, "failed", f"timed out after {config.COLLECTOR_TIMEOUT:.0f}s")
                log(f"{collector.NAME}: timed out")
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
    return [done[c.NAME] for c in collectors]


def _run_one(collector, ctx: Context, log) -> CollectorResult:
    started = time.monotonic()
    try:
        result = collector.collect(ctx)
    except MissingKey as e:
        result = CollectorResult(collector.NAME, "skipped", str(e))
    except Exception as e:  # fail-soft: one source never stops the run
        result = CollectorResult(collector.NAME, "failed", _short(e))
    result.duration_s = time.monotonic() - started
    log(f"{collector.NAME}: {result.status}, {len(result.facts)} facts" + (f" ({result.error})" if result.error else ""))
    return result


def _short(e: Exception) -> str:
    return f"{type(e).__name__}: {e}"[:300] if not isinstance(e, (RuntimeError, ValueError)) else str(e)[:300]
