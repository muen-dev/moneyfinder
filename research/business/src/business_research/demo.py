"""Seed a synthetic demo business (repo-root demo/<name>/) into the local, git-ignored data dirs.

A fixture folder holds profile.json (research/company format), business.json (signup answers) and inbox.jsonl
(messages in store.read_messages format). Everything in it is made up and its domain is a reserved .example name
listed in company_research.domain.DEMO_DOMAINS, so no collector ever runs against it.
"""

import json
import os
import shutil
from pathlib import Path

from company_research import store as company_store
from company_research.domain import is_demo_domain

from . import company, dossier, ids, store


def seed(fixture_dir: Path, *, use_llm: bool = True) -> tuple[dict, list[Path]]:
    """Copy the fixtures into place and build the dossier (email facts from the synthetic inbox). Idempotent."""
    fixture_dir = Path(fixture_dir)
    business = _read(fixture_dir / "business.json")
    profile = _read(fixture_dir / "profile.json")
    domain = business.get("domain")
    if not (business.get("demo") and profile.get("demo") and is_demo_domain(domain) and profile.get("domain") == domain):
        raise ValueError(f"{fixture_dir} is not a demo fixture: business.json and profile.json need demo: true and a "
                         "domain listed in company_research.domain.DEMO_DOMAINS")
    business_id = ids.check(business.get("business_id") or (profile.get("inputs") or {}).get("business_id") or "")

    research_dir = company_store.default_dir(domain)
    company_store._private_dir(research_dir)
    company_store.write_json(company_store.profile_path(research_dir), profile)
    company._write(company.business_dir(business_id) / "business.json", business)
    inbox = fixture_dir / "inbox.jsonl"
    target = store.messages_path(business_id)
    # Keep the file (and its mtime, which keys the cached email facts) when unchanged, so reruns skip Bedrock.
    if not target.exists() or target.read_bytes() != inbox.read_bytes():
        shutil.copy2(inbox, target)
        os.chmod(target, 0o600)

    result = dossier.build_for_domain(domain, use_llm=use_llm)  # writes research/company/data/<domain>/dossier.json
    paths = [dossier.dossier_path(research_dir), dossier.write_dossier(company.business_dir(business_id), result)]
    return result, paths


def _read(path: Path) -> dict:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"{path}: not a JSON object")
    return data
