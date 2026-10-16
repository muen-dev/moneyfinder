"""Heading-aware chunking. Each chunk carries its heading breadcrumb and PDF page number."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .extract import Page

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")


@dataclass
class Chunk:
    ordinal: int
    text: str
    heading: str | None
    page: int | None


def chunk_pages(pages: list[Page], max_chars: int = 1800, overlap_chars: int = 200) -> list[Chunk]:
    chunks: list[Chunk] = []
    trail: list[str] = []  # current heading path, e.g. ["Excelsior Jobs Program", "Eligibility"]

    for page in pages:
        buf: list[str] = []
        buf_heading: str | None = None

        for para in re.split(r"\n\s*\n", page.text):
            para = para.strip()
            if not para:
                continue
            first, _, rest = para.partition("\n")
            m = HEADING_RE.match(first)
            if m:
                _emit(chunks, buf, buf_heading, page.number)
                buf = []
                level = len(m.group(1))
                trail = trail[: level - 1] + [m.group(2).strip("# ")]
                # The heading lives in the breadcrumb prefix; keep only what follows it.
                para = rest.strip()
            heading = " > ".join(trail) or None
            if not para:
                continue
            if buf and heading != buf_heading:
                _emit(chunks, buf, buf_heading, page.number)
                buf = []
            buf_heading = heading
            for piece in _split_long(para, max_chars):
                if buf and sum(len(p) for p in buf) + len(piece) > max_chars:
                    _emit(chunks, buf, buf_heading, page.number)
                    # Carry the tail into the next chunk so sentences spanning a boundary stay findable.
                    buf = [buf[-1][-overlap_chars:]] if overlap_chars else []
                buf.append(piece)
        _emit(chunks, buf, buf_heading, page.number)

    return chunks


def _emit(chunks: list[Chunk], buf: list[str], heading: str | None, page: int | None) -> None:
    body = "\n\n".join(buf).strip()
    if body:
        prefix = f"{heading}\n\n" if heading else ""
        chunks.append(Chunk(len(chunks), prefix + body, heading, page))


def _split_long(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    pieces, current = [], ""
    for sentence in re.split(r"(?<=[.;:])\s+", text):
        while len(sentence) > max_chars:
            pieces.append(sentence[:max_chars])
            sentence = sentence[max_chars:]
        if len(current) + len(sentence) + 1 > max_chars:
            if current:
                pieces.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        pieces.append(current)
    return pieces
