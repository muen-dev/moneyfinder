"""Turn fetched bytes into page-numbered markdown text, plus outbound links for HTML."""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urljoin

from pypdf import PdfReader

from .fetch import Fetched


@dataclass
class Page:
    number: int | None
    text: str


@dataclass
class Extracted:
    title: str | None
    pages: list[Page]
    links: list[tuple[str, str]] = field(default_factory=list)  # (absolute url, anchor text)

    def markdown(self) -> str:
        """Single text for the lake; PDF page boundaries are kept as comments."""
        if len(self.pages) == 1 and self.pages[0].number is None:
            return self.pages[0].text
        return "\n\n".join(f"<!-- page {p.number} -->\n{p.text}" for p in self.pages)


class UnsupportedContent(ValueError):
    pass


def extract(fetched: Fetched) -> Extracted:
    if fetched.content_type == "application/pdf" or fetched.body[:5] == b"%PDF-":
        return _pdf(fetched.body)
    if fetched.content_type in ("text/html", "application/xhtml+xml"):
        parsed = _HTMLText(fetched.url)
        parsed.feed(fetched.body.decode(_charset(fetched.body), errors="replace"))
        text = fetched.markdown if fetched.markdown else parsed.text()
        return Extracted(title=fetched.title or parsed.title, pages=[Page(None, text)], links=parsed.links)
    if fetched.content_type.startswith("text/"):
        return Extracted(title=None, pages=[Page(None, fetched.body.decode("utf-8", errors="replace"))])
    raise UnsupportedContent(fetched.content_type)


def _pdf(body: bytes) -> Extracted:
    reader = PdfReader(io.BytesIO(body))
    # NYS form PDFs often separate words with tabs; normalize so full-text tokens and embeddings are clean.
    pages = [
        Page(i + 1, re.sub(r"[ \t]+", " ", page.extract_text() or "").strip()) for i, page in enumerate(reader.pages)
    ]
    title = reader.metadata.title if reader.metadata else None
    return Extracted(title=title or None, pages=[p for p in pages if p.text])


def _charset(body: bytes) -> str:
    m = re.search(rb'charset=["\']?([\w-]+)', body[:2048])
    return m.group(1).decode() if m else "utf-8"


class _HTMLText(HTMLParser):
    """Rough HTML-to-markdown fallback for when Firecrawl isn't configured. Also collects links."""

    SKIP = {"script", "style", "noscript", "nav", "header", "footer", "svg", "form"}
    BLOCK = {"p", "div", "section", "article", "li", "tr", "br", "table", "ul", "ol", "dd", "dt"}
    HEADING = {"h1": "#", "h2": "##", "h3": "###", "h4": "####", "h5": "#####", "h6": "######"}

    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.title: str | None = None
        self.links: list[tuple[str, str]] = []
        self._out: list[str] = []
        self._skip = 0
        self._in_title = False
        self._href: str | None = None
        self._anchor: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        elif tag == "title":
            self._in_title = True
        elif tag in self.HEADING:
            self._out.append(f"\n\n{self.HEADING[tag]} ")
        elif tag in self.BLOCK:
            self._out.append("\n")
        elif tag == "a":
            href = dict(attrs).get("href")
            if href and not href.startswith(("#", "mailto:", "tel:", "javascript:")):
                self._href, self._anchor = urljoin(self.base_url, href), []

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self._skip = max(0, self._skip - 1)
        elif tag == "title":
            self._in_title = False
        elif tag in self.HEADING:
            self._out.append("\n\n")
        elif tag == "a" and self._href:
            self.links.append((self._href.split("#")[0], " ".join("".join(self._anchor).split())))
            self._href = None

    def handle_data(self, data):
        if self._in_title:
            self.title = (self.title or "") + data.strip()
        if self._href is not None:
            self._anchor.append(data)
        if not self._skip:
            self._out.append(data)

    def text(self) -> str:
        text = "".join(self._out)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n[ \t]+", "\n", text)
        text = re.sub(r"^#+\s*$", "", text, flags=re.M)  # headings with no text
        return re.sub(r"\n{3,}", "\n\n", text).strip()
