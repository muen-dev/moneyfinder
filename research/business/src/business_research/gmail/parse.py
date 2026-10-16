"""Flatten Gmail API message resources into plain records for downstream analysis."""

import base64
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from email.message import Message
from email.utils import parseaddr
from html.parser import HTMLParser


@dataclass
class EmailMessage:
    id: str
    thread_id: str
    date: str  # ISO 8601 UTC, from Gmail's receive time
    sender: str  # raw From header, e.g. "Gusto <no-reply@gusto.com>"
    sender_domain: str  # e.g. "gusto.com"; vendors and agencies show up here
    to: str
    subject: str
    snippet: str
    body: str  # text/plain parts, or text extracted from HTML when there are none
    labels: list[str] = field(default_factory=list)
    attachments: list[str] = field(default_factory=list)  # filenames only; contents are not downloaded

    def to_dict(self) -> dict:
        return asdict(self)


def parse_message(raw: dict) -> EmailMessage:
    """Parse a messages.get response requested with format="full"."""
    payload = raw.get("payload", {})
    headers = _headers(payload)
    plain: list[str] = []
    html: list[str] = []
    attachments: list[str] = []
    _walk(payload, plain, html, attachments)

    sender = headers.get("from", "")
    address = parseaddr(sender)[1]
    return EmailMessage(
        id=raw["id"],
        thread_id=raw.get("threadId", ""),
        date=datetime.fromtimestamp(int(raw.get("internalDate", 0)) / 1000, UTC).isoformat(),
        sender=sender,
        sender_domain=address.rpartition("@")[2].lower(),
        to=headers.get("to", ""),
        subject=headers.get("subject", ""),
        snippet=raw.get("snippet", ""),
        body=("\n".join(plain) if plain else _html_to_text("\n".join(html))).strip(),
        labels=raw.get("labelIds", []),
        attachments=attachments,
    )


def _headers(part: dict) -> dict[str, str]:
    return {h["name"].lower(): h["value"] for h in part.get("headers", [])}


def _walk(part: dict, plain: list[str], html: list[str], attachments: list[str]) -> None:
    mime = part.get("mimeType", "")
    if part.get("filename"):
        attachments.append(part["filename"])
    elif mime == "text/plain":
        plain.append(_decode(part))
    elif mime == "text/html":
        html.append(_decode(part))
    for child in part.get("parts", []):
        _walk(child, plain, html, attachments)


def _decode(part: dict) -> str:
    data = part.get("body", {}).get("data", "")
    raw = base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))
    # Gmail returns the part's bytes in its declared charset, which is not always UTF-8.
    content_type = Message()
    content_type["content-type"] = _headers(part).get("content-type", "text/plain")
    try:
        return raw.decode(content_type.get_content_charset() or "utf-8", errors="replace")
    except LookupError:
        return raw.decode("utf-8", errors="replace")


class _TextExtractor(HTMLParser):
    SKIP = {"script", "style"}

    def __init__(self):
        super().__init__()
        self.chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data):
        if not self._skip_depth and data.strip():
            self.chunks.append(data.strip())


def _html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    return "\n".join(parser.chunks)
