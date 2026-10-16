"""Collectors: each gathers facts from one public source and fails on its own.

The website runs first because its company name, address and LinkedIn link steer the others.
"""

import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit, urlunsplit

from ..profile import Fact, Source
from ..providers import Providers


@dataclass
class Context:
    domain: str
    providers: Providers
    names: list[str] = field(default_factory=list)  # best first: brand name, legal name, ...
    city: str | None = None
    linkedin_url: str | None = None

    @property
    def name(self) -> str:
        return self.names[0] if self.names else guess_name(self.domain)

    def add_name(self, name: str | None) -> None:
        name = (name or "").strip()
        if 2 <= len(name) <= 80 and name.lower() not in (n.lower() for n in self.names):
            self.names.append(name)


def guess_name(domain: str) -> str:
    """'joes-pizza.com' -> 'Joes Pizza'. Only used until a real name is found."""
    label = domain.split(".")[0]
    return re.sub(r"[-_]+", " ", label).title()


def fact(field_name: str, value, url: str, via: str, fetched_at: str, confidence: float, collector: str, note: str = "") -> Fact:
    return Fact(field_name, value, Source(url, via, fetched_at), confidence, collector, note)


def strip_url(url: str) -> str:
    """Drop query string and fragment (tracking params; BBB disallows crawling '?' URLs)."""
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc.lower(), parts.path, "", ""))


def same_site(url: str, domain: str) -> bool:
    host = (urlsplit(url).hostname or "").lower()
    return urlsplit(url).scheme in ("http", "https") and (host == domain or host.endswith(f".{domain}"))


def mentions(text: str, names: list[str], domain: str) -> bool:
    lowered = text.lower()
    if domain in lowered:
        return True
    return any(len(n) >= 3 and n.lower() in lowered for n in names)
