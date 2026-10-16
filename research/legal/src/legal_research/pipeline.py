"""Build the tax-credit catalog: find programs, read their official pages, attach claim counts, tag niches.

    index pages ──► programs ◄── programs.toml (federal, extra NYC, corrections)
                       │
          official page per program ──► eligibility, amount, forms, links, updated, status hints
                       │
       data.ny.gov claim counts ──► claimants, dollars, certifying agency (NYS)
                       │
              niches.toml ──► niches ──► data/catalog.json

Every step fails on its own: a page that can't be read leaves its program in the catalog with the error.
"""

import shutil
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path

from . import catalog, claims, config, parse, store
from .catalog import Program
from .providers import ProviderError, Providers, Recorder, now, official_url

SCHEMA_VERSION = 1
SEARCH_DOMAINS = ["tax.ny.gov", "esd.ny.gov", "dol.ny.gov", "nyc.gov", "irs.gov", "ny.gov"]


def run(
    *,
    providers: Providers | None = None,
    out_dir: Path | None = None,
    catalog_dir: Path | None = None,
    pages: bool = True,
    with_claims: bool = True,
    search: bool = False,
    only: list[str] | None = None,
    log: Callable[[str], None] = lambda message: None,
) -> dict:
    out_dir = out_dir or config.DATA_DIR
    own = providers is None
    providers = providers or Providers(Recorder())
    sources = catalog.load_sources(catalog_dir)
    niches = catalog.load_niches(catalog_dir)
    curated = catalog.load_programs(catalog_dir, {n.id for n in niches})
    report: dict = {"indexes": [], "datasets": []}
    try:
        programs = discover(providers, sources, curated, report, log)
        if only:
            unknown = set(only) - set(programs)
            if unknown:
                raise ValueError(f"unknown program id(s): {', '.join(sorted(unknown))}")
            programs = {pid: p for pid, p in programs.items() if pid in only}
        if pages:
            read_pages(providers, list(programs.values()), out_dir / "pages", log)
        unmatched = attach_claims(providers, sources, list(programs.values()), report, log) if with_claims else []
        for program in programs.values():
            finish(program, niches)
        candidates = search_niches(providers, niches, programs.values(), log) if search else []
    finally:
        if own:
            providers.close()

    result = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now(),
        "programs": [asdict(p) for p in sorted(programs.values(), key=lambda p: (p.jurisdiction, p.id))],
        "niches": [
            {**asdict(n), "programs": sorted(p.id for p in programs.values() if n.id in p.niches)} for n in niches
        ],
        "unmatched_claims": unmatched,
        "candidates": candidates,
        **report,
    }
    store.write_json(store.catalog_path(out_dir), result)
    store.write_json(out_dir / "calls.json", providers.recorder.dump())
    return result


def discover(providers: Providers, sources: catalog.Sources, curated: list[Program], report: dict, log) -> dict[str, Program]:
    programs: dict[str, Program] = {}
    for index in sources.indexes:
        try:
            page = providers.page(index.url)
            links = parse.index_links(page.html, page.final_url, index.follow, index.skip)
            for url, anchor in links:
                catalog.add_discovered(programs, index, url, anchor)
            report["indexes"].append({"id": index.id, "url": index.url, "status": "ok", "links": len(links)})
            log(f"index {index.id}: {len(links)} program links")
        except ProviderError as e:
            report["indexes"].append({"id": index.id, "url": index.url, "status": "failed", "error": str(e)[:300]})
            log(f"index {index.id}: failed ({e})")
    catalog.apply_curated(programs, curated)
    return programs


def read_pages(providers: Providers, programs: list[Program], pages_dir: Path, log) -> None:
    shutil.rmtree(pages_dir, ignore_errors=True)
    ok = 0
    for program in programs:
        try:
            page = providers.page(program.url)
            program.page = {"status": "ok", "final_url": page.final_url, "via": page.via, "fetched_at": page.fetched_at}
            if "html" not in page.content_type:
                program.page |= {"status": "skipped", "error": f"not HTML ({page.content_type})"}
                continue
            program.facts = parse.program_page(page.html, page.final_url)
            store.write_text(pages_dir / f"{program.id}.html", page.html)
            ok += 1
        except ProviderError as e:
            program.page = {"status": "failed", "error": str(e)[:300]}
            log(f"page {program.id}: failed ({e})")
    log(f"pages: {ok}/{len(programs)} read")


def attach_claims(providers: Providers, sources: catalog.Sources, programs: list[Program], report: dict, log) -> list[dict]:
    unmatched = []
    for dataset in sources.datasets:
        try:
            summaries = claims.summarize(claims.fetch(providers, dataset), dataset)
            left = claims.attach(programs, summaries)
            unmatched += left
            report["datasets"].append({"id": dataset.id, "status": "ok", "credits": len(summaries), "unmatched": len(left)})
            log(f"claims {dataset.id}: {len(summaries)} credits, {len(summaries) - len(left)} matched to programs")
        except ProviderError as e:
            report["datasets"].append({"id": dataset.id, "status": "failed", "error": str(e)[:300]})
            log(f"claims {dataset.id}: failed ({e})")
    return unmatched


def finish(program: Program, niches: list[catalog.Niche]) -> None:
    """Niches, pre-approval and a status with the reason for it."""
    names = " | ".join([program.name, *program.aliases, program.facts.get("title", "")])
    for niche in niches:
        if niche.id not in program.niches and niche.matches(names):
            program.niches.append(niche.id)

    agencies = [c["certifying_agency"] for c in program.claims if c.get("certifying_agency")]
    program.certifying_agency = agencies[0] if agencies else None
    hinted = program.facts.get("hints", {}).get("preapproval")
    program.requires_preapproval = True if agencies else (hinted if program.facts else None)

    if program.status != "unknown":
        program.status_basis = "curated"
        return
    hints = program.facts.get("hints", {}).get("status", [])
    recent = [c for c in program.claims if (c.get("taxpayers") or 0) > 0 and c["latest_year"] >= config.FORM_TAX_YEAR - 3]
    if program.page.get("status") == "ok" and recent and not hints:
        program.status = "active"
        program.status_basis = f"official page live, {recent[0]['taxpayers']} claimants in {recent[0]['latest_year']}, no expiry wording"
    else:
        reasons = []
        if program.page.get("status") != "ok":
            reasons.append("page not read")
        if hints:
            reasons.append("page mentions dates or expiry; read status hints")
        if not recent:
            reasons.append("no recent claims data")
        program.status_basis = "; ".join(reasons)


def search_niches(providers: Providers, niches: list[catalog.Niche], programs, log) -> list[dict]:
    """Ask a search API for official pages per niche that the catalog doesn't have yet. Leads only: never fetched."""
    known = set()
    for p in programs:
        known.add(p.url)
        known.update(link["url"] for link in p.facts.get("links", []))
    candidates, seen = [], set()
    for niche in niches:
        query = niche.search or f"New York {niche.label} business tax credit"
        try:
            results, provider = providers.search(query, SEARCH_DOMAINS)
        except ProviderError as e:
            log(f"search {niche.id}: failed ({e})")
            if "no API key" in str(e):
                break
            continue
        for r in results:
            url = official_url(r.get("url") or "")
            if not url or url in known or url in seen:
                continue
            seen.add(url)
            candidates.append({
                "niche": niche.id, "url": url, "title": parse.clean(r.get("title") or "", 200),
                "snippet": parse.clean(r.get("content") or "", 400), "via": provider, "query": query,
            })
    log(f"search: {len(candidates)} new official pages to review")
    return candidates
