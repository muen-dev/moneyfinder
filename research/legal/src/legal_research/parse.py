"""Read official program pages: sections, links, forms, dates and status hints.

Page text is untrusted data. It is kept as short, single-line strings and never interpreted.
Only links to official hosts survive (see providers.official_url).
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

from . import config
from .providers import official_url

SKIP_TAGS = {"script", "style", "noscript", "svg", "nav", "footer", "button", "select", "template"}
BLOCK_TAGS = {"p", "div", "li", "ul", "ol", "table", "tr", "td", "th", "section", "article", "br", "dd", "dt", "blockquote", "main"}
HEADINGS = {"h1", "h2", "h3", "h4"}


@dataclass
class Doc:
    title: str = ""
    blocks: list[tuple[str, str]] = field(default_factory=list)  # (h1..h4 | p, text)
    links: list[tuple[str, str]] = field(default_factory=list)  # (official https url, anchor text)

    @property
    def h1(self) -> str:
        return next((text for kind, text in self.blocks if kind == "h1"), "") or self.title

    def sections(self) -> list[tuple[str, str]]:
        """(heading, body text) pairs, in page order. Text before the first heading has heading ''."""
        out: list[tuple[str, list[str]]] = [("", [])]
        for kind, text in self.blocks:
            if kind in HEADINGS and kind != "h1":
                out.append((text, []))
            elif kind == "p":
                out[-1][1].append(text)
        return [(heading, " ".join(body)) for heading, body in out if heading or body]


class _Reader(HTMLParser):
    def __init__(self, base: str, root: str):
        super().__init__(convert_charrefs=True)
        self.base, self.root = base, root  # root: "main" (a <main> or role=main) or "id-main"
        self.doc = Doc()
        self._skip = 0
        self._root_tag: str | None = None
        self._root_depth = 0
        self._in_title = False
        self._kind = "p"
        self._buf: list[str] = []
        self._href: str | None = None
        self._anchor: list[str] = []

    def _is_root(self, tag: str, attrs: dict) -> bool:
        if self.root == "main":
            return tag == "main" or attrs.get("role") == "main"
        return attrs.get("id") == "main"

    def handle_starttag(self, tag, attrs):
        a = {k: v or "" for k, v in attrs}
        if tag == "title":
            self._in_title = True
        if self._root_tag is None and self._is_root(tag, a):
            self._root_tag, self._root_depth = tag, 0
        if self._root_tag == tag:
            self._root_depth += 1
        if tag in SKIP_TAGS or (tag == "header" and not self._root_tag):
            self._skip += 1
            return
        if tag in HEADINGS or tag in BLOCK_TAGS:
            self._flush()
            self._kind = tag if tag in HEADINGS else "p"
        if tag == "a" and self._active():
            self._href, self._anchor = a.get("href", ""), []

    def handle_startendtag(self, tag, attrs):
        if tag == "br":
            self._flush()

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag in SKIP_TAGS or (tag == "header" and not self._root_tag):
            self._skip = max(0, self._skip - 1)
        elif tag == "a" and self._href is not None:
            url = official_url(urljoin(self.base, self._href)) if not self._href.startswith(("mailto:", "tel:", "javascript:", "#")) else None
            if url:
                self.doc.links.append((url, clean(" ".join(self._anchor), 160)))
            self._href = None
        elif tag in HEADINGS or tag in BLOCK_TAGS:
            self._flush()
            self._kind = "p"
        if self._root_tag == tag:
            self._root_depth -= 1
            if self._root_depth == 0:
                self._flush()
                self._root_tag = "done"

    def handle_data(self, data):
        if self._in_title:
            self.doc.title += data
            return
        if not self._active():
            return
        self._buf.append(data)
        if self._href is not None:
            self._anchor.append(data)

    def _active(self) -> bool:
        return self._skip == 0 and self._root_tag not in (None, "done")

    def _flush(self):
        text = clean(" ".join(self._buf), config.MAX_SECTION_CHARS)
        if text:
            self.doc.blocks.append((self._kind, text))
        self._buf = []

    def close(self):
        super().close()
        self._flush()
        self.doc.title = clean(self.doc.title, 200)


def read(html: str, base: str) -> Doc:
    """Main content of a page: <main> (or role=main) if present, else the element with id="main", else the body."""
    if re.search(r"<main\b|role=[\"']main[\"']", html, re.I):
        root = "main"
    elif re.search(r"\bid=[\"']main[\"']", html, re.I):
        root = "id-main"
    else:
        html, root = f'<div id="main">{html}</div>', "id-main"
    reader = _Reader(base, root)
    reader.feed(html)
    reader.close()
    return reader.doc


def clean(value: str, limit: int = 600) -> str:
    """Single-line text without control or bidi characters, bounded length."""
    text = re.sub(r"[\x00-\x1f\x7f​-‏‪-‮⁦-⁩]+", " ", str(value))
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


# Links

def authority(url: str) -> str:
    """kb source authority for an official URL, from its shape."""
    parts = urlsplit(url)
    host, path = parts.hostname or "", parts.path.lower()
    if host in ("www.nysenate.gov", "legislation.nysenate.gov", "codelibrary.amlegal.com") or "/legislation/laws/" in path:
        return "statute"
    if host in ("data.ny.gov", "data.cityofnewyork.us"):
        return "dataset"
    if form := form_from_url(url):
        return form[1]
    if path.endswith(".pdf"):
        return "form" if re.search(r"applica|form", path) else "agency_guidance"
    if host in ("www.tax.ny.gov", "www.irs.gov", "www.nyc.gov", "www1.nyc.gov"):
        return "agency_guidance"
    return "program_page"


FORM_IN_TEXT = re.compile(
    r"\b((?:CT|IT|DTF|NYC|RP|ST|MT|TP|AU)-\d{1,4}(?:\.\d+)?[A-Z]?(?:-[A-Z]{1,4})?)\b|\bForms?\s+(\d{4}(?:-[A-Z])?)\b"
)


def form_from_url(url: str) -> tuple[str, str] | None:
    """(code, 'form' | 'form_instructions') for NYS DTF and IRS form PDFs, e.g. ct607i.pdf -> ('CT-607', instructions)."""
    path = urlsplit(url).path.lower()
    m = re.search(r"/current_forms/[a-z]+/(ct|it|dtf|st|mt|tp|au)(\d{1,4}(?:\.\d+)?[a-z]??)(i)?(?:_fill_in)?\.pdf$", path)
    if m:
        return f"{m.group(1).upper()}-{m.group(2).upper()}", "form_instructions" if m.group(3) else "form"
    m = re.search(r"/irs-pdf/([fi])(\d{4}[a-z]?)\.pdf$", path)
    if m:
        return m.group(2).upper(), "form_instructions" if m.group(1) == "i" else "form"
    m = re.search(r"/(?:forms-pubs/about-form-|instructions/i)(\d{4}[a-z]?)$", path)
    if m:
        return m.group(1).upper(), "form_instructions" if "/instructions/" in path else "form"
    return None


def form_from_text(text: str) -> str | None:
    m = FORM_IN_TEXT.search(text or "")
    return (m.group(1) or m.group(2)).upper() if m else None


# Program pages

ELIGIBILITY = re.compile(r"eligib|who (can|may|qualif)|qualif|requirement", re.I)
AMOUNT = re.compile(r"how much|amount|benefit|value of the|credit (is|equals)|calculat", re.I)
STATUS_HINT = re.compile(
    r"[^.]*\b(expired?|no longer (available|accept\w*)|sunset|repealed|closed to new|not available for tax years|"
    r"(applications?|deadline)[^.]{0,40}\b(due|by|before|until|no later than)|through (tax year|december)|"
    r"taxable years? beginning (on or )?(after|before)|hiatus|lapsed)\b[^.]*\.?",
    re.I,
)
PREAPPROVAL = re.compile(
    r"certificate (of (tax credit|eligibility|completion|entitlement))?|must (first )?apply|approved participant|"
    r"preliminary (schedule|approval)|application (to|with) (empire state development|esd|the department of labor)|"
    r"certif(ied|ication) (by|from)",
    re.I,
)
UPDATED = re.compile(r"(?:Updated|Last updated|Page last reviewed or updated)\s*:?\s*([A-Z][a-z]+\.? \d{1,2}, \d{4})")


def program_page(html: str, url: str) -> dict:
    """Structured facts from one program page: what the matching and form-filling agents need first."""
    doc = read(html, url)
    sections = doc.sections()
    text = " ".join(body for _, body in sections)

    def section(pattern: re.Pattern) -> str:
        for heading, body in sections:
            if heading and pattern.search(heading) and body:
                return clean(body, config.MAX_SECTION_CHARS)
        return ""

    lead = next((body for heading, body in sections if body), "")
    forms: dict[str, dict] = {}
    links = []
    seen = {official_url(url)}
    for link, anchor in doc.links:
        if link in seen:
            continue
        seen.add(link)
        kind = authority(link)
        hit = form_from_url(link)
        code = hit[0] if hit else (form_from_text(anchor) if link.lower().endswith(".pdf") else None)
        if code:
            entry = forms.setdefault(code, {"code": code, "title": "", "pdf": None, "instructions": None, "page": None})
            if (hit and hit[1] == "form_instructions") or re.search(r"\binstructions\b", anchor, re.I):
                slot = "instructions"
            else:
                slot = "pdf" if link.lower().endswith(".pdf") else "page"
            entry[slot] = entry[slot] or link
            title = re.sub(rf"^(Form\s+)?{re.escape(code)}\s*,?\s*", "", anchor, flags=re.I).strip(" ,")
            if title and title.lower() not in ("instructions", "form") and not entry["title"]:
                entry["title"] = title
        links.append({"url": link, "title": anchor, "authority": kind})

    updated = None
    if m := UPDATED.search(text):
        for fmt in ("%B %d, %Y", "%b %d, %Y", "%b. %d, %Y"):
            try:
                updated = datetime.strptime(m.group(1), fmt).date().isoformat()
                break
            except ValueError:
                continue

    lowered = text.lower()
    refundable = None
    if re.search(r"\b(not refundable|nonrefundable|non-refundable)\b", lowered):
        refundable = False
    elif re.search(r"\brefundable\b", lowered):
        refundable = True

    return {
        "title": doc.h1,
        "summary": clean(lead, 600),
        "eligibility": section(ELIGIBILITY),
        "amount": section(AMOUNT),
        "sections": [heading for heading, _ in sections if heading][:20],
        "forms": list(forms.values()),
        "links": links,
        "updated": updated,
        "hints": {
            "refundable": refundable,
            "preapproval": bool(PREAPPROVAL.search(text)),
            "status": [clean(m.group(0), 240) for m in STATUS_HINT.finditer(text)][:5],
        },
    }


def index_links(html: str, base: str, follow: list[str], skip: list[str]) -> list[tuple[str, str]]:
    """(url, anchor) for links on an index page matching a `follow` regex and no `skip` regex.

    One page can cover several credits, so a URL may appear with more than one anchor.
    """
    keep = [re.compile(p) for p in follow]
    drop = [re.compile(p) for p in skip]
    out, seen = [], set()
    for url, anchor in read(html, base).links:
        if not anchor or (url, anchor) in seen or not any(p.search(url) for p in keep) or any(p.search(url) for p in drop):
            continue
        seen.add((url, anchor))
        out.append((url, anchor))
    return out
