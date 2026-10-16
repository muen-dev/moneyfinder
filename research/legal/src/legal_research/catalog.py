"""The hand-maintained inputs in research/legal/catalog/, and the Program records built from them.

- sources.toml   index pages that list programs, and datasets with per-credit claim counts
- programs.toml  programs no index lists (federal, some NYC), plus corrections to discovered ones
- niches.toml    who each credit is really for, with name patterns, NAICS prefixes and profile keywords
"""

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

from . import config
from .providers import official_url

JURISDICTIONS = ("NYS", "NYC", "federal")
KINDS = ("credit", "exemption", "abatement", "refund", "deduction", "grant")  # kb incentive.kind
STATUSES = ("active", "expired", "unknown")  # kb incentive.status
ID_PREFIX = {"NYS": "nys", "NYC": "nyc", "federal": "fed"}


class CatalogError(ValueError):
    pass


@dataclass
class Index:
    id: str
    url: str
    jurisdiction: str
    agency: str
    follow: list[str]
    skip: list[str] = field(default_factory=list)
    tax_types: list[str] = field(default_factory=list)


@dataclass
class Dataset:
    id: str
    host: str
    dataset: str
    title: str
    jurisdiction: str = "NYS"


@dataclass
class Niche:
    id: str
    label: str
    description: str = ""
    naics: list[str] = field(default_factory=list)
    name_patterns: list[str] = field(default_factory=list)
    profile_keywords: list[str] = field(default_factory=list)
    # program id -> the keywords that are evidence for that program, for niches grouping several topics
    program_keywords: dict[str, list[str]] = field(default_factory=dict)
    search: str = ""  # query for `run --search`; defaults to the label

    def matches(self, text: str) -> bool:
        return any(re.search(p, text, re.I) for p in self.name_patterns)


@dataclass
class Program:
    id: str
    name: str
    jurisdiction: str
    url: str
    agency: str | None = None
    kind: str = "credit"
    aliases: list[str] = field(default_factory=list)
    tax_types: list[str] = field(default_factory=list)
    status: str = "unknown"
    status_note: str = ""
    status_basis: str = ""
    niches: list[str] = field(default_factory=list)
    claims_names: list[str] = field(default_factory=list)  # credit names in the claims datasets, when they differ
    links: list[dict] = field(default_factory=list)  # curated extra links: {url, title, authority}
    note: str = ""
    found_in: list[str] = field(default_factory=list)  # index ids, or "curated"
    # Filled in by the pipeline
    page: dict = field(default_factory=dict)  # fetch status of url
    facts: dict = field(default_factory=dict)  # parse.program_page output
    claims: list[dict] = field(default_factory=list)  # claims.summarize entries matched to this program
    requires_preapproval: bool | None = None
    certifying_agency: str | None = None


@dataclass
class Sources:
    indexes: list[Index]
    datasets: list[Dataset]


def program_id(jurisdiction: str, url: str) -> str:
    """Stable id from the page URL: .../pit/credits/hire_a_veteran_credit.htm -> nys_hire_a_veteran."""
    stem = PurePosixPath(urlsplit(url).path).stem.lower()
    stem = re.sub(r"^(business|benefits|property|landlords|about-form)-", "", stem)
    stem = re.sub(r"[^a-z0-9]+", "_", stem).strip("_")
    stem = re.sub(r"_(tax_)?credits?(_program)?$", "", stem) or stem
    return f"{ID_PREFIX[jurisdiction]}_{stem}"


def kind_from_name(name: str) -> str:
    lowered = name.lower()
    for word, kind in (("abatement", "abatement"), ("exemption", "exemption"), ("deduction", "deduction"), ("grant", "grant"), ("refund", "refund")):
        if word in lowered:
            return kind
    return "credit"


def _read(path: Path) -> dict:
    try:
        return tomllib.loads(path.read_text())
    except (OSError, tomllib.TOMLDecodeError) as e:
        raise CatalogError(f"{path.name}: {e}") from e


def _official(url: str, where: str) -> str:
    checked = official_url(url)
    if not checked or not url.startswith("https://"):
        raise CatalogError(f"{where}: {url!r} must be an https URL on an official host")
    return checked


def _patterns(patterns: list[str], where: str) -> list[str]:
    for p in patterns:
        try:
            re.compile(p)
        except re.error as e:
            raise CatalogError(f"{where}: bad regex {p!r}: {e}") from e
    return patterns


def load_sources(directory: Path | None = None) -> Sources:
    data = _read((directory or config.CATALOG_DIR) / "sources.toml")
    indexes = []
    for entry in data.get("index", []):
        index = Index(**entry)
        where = f"sources.toml index {index.id}"
        index.url = _official(index.url, where)
        if index.jurisdiction not in JURISDICTIONS:
            raise CatalogError(f"{where}: jurisdiction must be one of {JURISDICTIONS}")
        _patterns(index.follow + index.skip, where)
        indexes.append(index)
    datasets = [Dataset(**entry) for entry in data.get("dataset", [])]
    _unique([i.id for i in indexes] + [d.id for d in datasets], "sources.toml")
    return Sources(indexes, datasets)


def load_niches(directory: Path | None = None) -> list[Niche]:
    niches = [Niche(**entry) for entry in _read((directory or config.CATALOG_DIR) / "niches.toml").get("niche", [])]
    for niche in niches:
        _patterns(niche.name_patterns, f"niches.toml {niche.id}")
    _unique([n.id for n in niches], "niches.toml")
    return niches


def load_programs(directory: Path | None = None, niche_ids: set[str] | None = None) -> list[Program]:
    """Curated programs. An entry whose id matches a discovered program corrects it instead of adding one."""
    programs = []
    for entry in _read((directory or config.CATALOG_DIR) / "programs.toml").get("program", []):
        program = Program(**{"name": "", "jurisdiction": "", "url": "", **entry})
        where = f"programs.toml {program.id}"
        if program.url:
            program.url = _official(program.url, where)
        for link in program.links:
            link["url"] = _official(link["url"], where)
        if program.jurisdiction and program.jurisdiction not in JURISDICTIONS:
            raise CatalogError(f"{where}: jurisdiction must be one of {JURISDICTIONS}")
        if program.kind not in KINDS or program.status not in STATUSES:
            raise CatalogError(f"{where}: kind must be one of {KINDS}, status one of {STATUSES}")
        if niche_ids is not None and (unknown := set(program.niches) - niche_ids):
            raise CatalogError(f"{where}: unknown niche(s) {sorted(unknown)}")
        programs.append(program)
    _unique([p.id for p in programs], "programs.toml")
    return programs


def _unique(ids: list[str], where: str) -> None:
    seen = set()
    for i in ids:
        if i in seen:
            raise CatalogError(f"{where}: duplicate id {i!r}")
        seen.add(i)


def add_discovered(programs: dict[str, Program], index: Index, url: str, anchor: str) -> Program:
    """Add a program found on an index page, or merge a second sighting (another index, or another credit on the same page)."""
    pid = program_id(index.jurisdiction, url)
    program = programs.get(pid)
    if program is None:
        program = programs[pid] = Program(
            id=pid, name=anchor, jurisdiction=index.jurisdiction, url=url, agency=index.agency, kind=kind_from_name(anchor)
        )
    elif anchor.lower() != program.name.lower() and anchor.lower() not in (a.lower() for a in program.aliases):
        program.aliases.append(anchor)
    for tax_type in index.tax_types:
        if tax_type not in program.tax_types:
            program.tax_types.append(tax_type)
    if index.id not in program.found_in:
        program.found_in.append(index.id)
    return program


def apply_curated(programs: dict[str, Program], curated: list[Program]) -> None:
    """Curated values win over discovered ones; lists are merged."""
    for entry in curated:
        program = programs.get(entry.id)
        if program is None:
            if not (entry.name and entry.url and entry.jurisdiction):
                continue  # a correction to a program whose index page wasn't read this run
            entry.found_in = ["curated"]
            programs[entry.id] = entry
            continue
        for name in ("name", "agency", "status_note", "note", "url"):
            if value := getattr(entry, name):
                setattr(program, name, value)
        if entry.kind != "credit":
            program.kind = entry.kind
        if entry.status != "unknown":
            program.status = entry.status
        for name in ("aliases", "tax_types", "niches", "claims_names", "links"):
            merged = getattr(program, name)
            merged.extend(v for v in getattr(entry, name) if v not in merged)
        program.found_in.append("curated")
