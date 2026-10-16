"""Company domains: normalize user input to a public registrable domain, or reject it."""

import ipaddress
import re
from urllib.parse import urlsplit

from publicsuffixlist import PublicSuffixList

_PSL = PublicSuffixList(accept_unknown=False)
_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")

# Special-use and private names that never identify a company's public website.
_BLOCKED_SUFFIXES = (
    "localhost", "local", "internal", "intranet", "lan", "home", "corp", "private",
    "test", "example", "invalid", "onion", "arpa", "home.arpa",
)

# Mailbox providers: an address there says nothing about the owner's company domain.
FREE_EMAIL_DOMAINS = frozenset(
    {
        "gmail.com", "googlemail.com",
        "yahoo.com", "yahoo.co.uk", "yahoo.ca", "ymail.com", "rocketmail.com",
        "outlook.com", "hotmail.com", "hotmail.co.uk", "live.com", "msn.com", "passport.com",
        "icloud.com", "me.com", "mac.com",
        "aol.com", "aim.com", "verizon.net", "att.net", "sbcglobal.net", "comcast.net",
        "optonline.net", "earthlink.net", "charter.net", "cox.net",
        "proton.me", "protonmail.com", "protonmail.ch", "pm.me",
        "gmx.com", "gmx.net", "gmx.de", "mail.com", "email.com", "zoho.com", "zohomail.com",
        "yandex.com", "yandex.ru", "fastmail.com", "hey.com", "tutanota.com", "tuta.io",
        "hushmail.com", "inbox.com", "qq.com", "163.com", "126.com",
    }
)


# Synthetic demo businesses (repo-root demo/). Reserved .example names can never be a real site, so they are
# accepted only when reading stored data (normalize_stored); signup and research still reject them via normalize.
DEMO_DOMAINS = frozenset({"gowanuskettle.example"})


class InvalidDomain(ValueError):
    """The input isn't a public company domain we can research."""


def normalize(raw: str) -> str:
    """Return the registrable domain for user input like 'https://www.Shop.Example.com/about'.

    Strips scheme, path, 'www.' and subdomains; rejects IPs, ports, credentials, special-use
    names and anything without a public suffix.
    """
    text = (raw or "").strip().lower()
    if not text:
        raise InvalidDomain("Enter your company's website domain, e.g. joespizza.com.")
    if len(text) > 300 or any(c.isspace() or ord(c) < 0x21 for c in text):
        raise InvalidDomain("That doesn't look like a domain.")
    if "@" in text and "://" not in text and "/" not in text:
        text = text.rsplit("@", 1)[1]  # someone pasted an email address
    parts = urlsplit(text if "://" in text else f"//{text}")
    if parts.scheme and parts.scheme not in ("http", "https"):
        raise InvalidDomain("Only http(s) website addresses are accepted.")
    if parts.username is not None or parts.password is not None:
        raise InvalidDomain("Remove the user name or password from the address.")
    try:
        port = parts.port
    except ValueError:
        port = -1
    if port is not None or parts.netloc.endswith(":"):
        raise InvalidDomain("Remove the port number; enter just the domain.")
    host = (parts.hostname or "").rstrip(".")
    if not host:
        raise InvalidDomain("That doesn't look like a domain.")
    if _is_ip(host):
        raise InvalidDomain("Enter a domain name, not an IP address.")
    try:
        host = host.encode("idna").decode("ascii")
    except UnicodeError as e:
        raise InvalidDomain("That domain has characters we can't use.") from e
    if len(host) > 253 or not all(_LABEL.fullmatch(label) for label in host.split(".")):
        raise InvalidDomain("That doesn't look like a domain.")
    if host == "localhost" or any(host == s or host.endswith(f".{s}") for s in _BLOCKED_SUFFIXES):
        raise InvalidDomain("That's a private or reserved name, not a public website.")
    registrable = _PSL.privatesuffix(host)
    if not registrable:
        raise InvalidDomain("That isn't a public domain (it needs a real suffix like .com or .nyc).")
    return registrable


def normalize_stored(raw: str) -> str:
    """normalize(), plus the synthetic demo domains: for looking up stored profiles and dossiers only."""
    text = (raw or "").strip().lower()
    return text if text in DEMO_DOMAINS else normalize(raw)


def is_demo_domain(domain: str | None) -> bool:
    return (domain or "").strip().lower() in DEMO_DOMAINS


def is_free_email_domain(domain: str) -> bool:
    domain = domain.lower().strip(".")
    return domain in FREE_EMAIL_DOMAINS or domain.split(".")[0] in {"yahoo", "hotmail", "outlook", "gmx", "yandex"}


def from_email(email: str) -> str | None:
    """Company domain suggested by an email address, or None for personal mailbox providers."""
    if "@" not in (email or ""):
        return None
    try:
        domain = normalize(email.rsplit("@", 1)[1])
    except InvalidDomain:
        return None
    return None if is_free_email_domain(domain) else domain


def slug(domain: str) -> str:
    """Filesystem-safe directory name for a normalized domain."""
    return re.sub(r"[^a-z0-9.-]", "-", domain)


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host.strip("[]"))
        return True
    except ValueError:
        pass
    # Shorthand IPv4 like 127.1 that resolvers still accept. (Hex forms fail the suffix check.)
    return bool(re.fullmatch(r"[0-9.]+", host))
