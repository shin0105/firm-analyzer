#!/usr/bin/env python3
"""Read the per-firm result folders that summarize writes.

Layout, one folder per firm::

    <output.directory>/<category_id>/<firm>/
        summary.md          # "# name", **Field:** header lines, the AI notice,
                            # then the body and a 출처 (Sources) list
        raw_search.json     # the Tavily response the summary was built from
        webpage.json        # optional: verified official webpage
        segmentation.json   # optional: multi-axis taxonomy record

The folders are the source of truth. The `<category>_firms.csv` files next to
them are append-only side outputs and drift, so anything that needs the full
picture (export, segmentation backfill) reads the folders through here.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional

from firm_analyzer.core import segmentation as seg
from firm_analyzer.notice import AI_NOTICE_MARKDOWN, NOTICE_MARKER, SOURCES_HEADING

HEADER_FIELD = re.compile(r"^\*\*([^*]+?):\*\*\s*(.*)$")
SEGMENTATION_HEADING = "## 세분류 (Segmentation)"
# Inline emphasis and list markers, stripped when flattening prose to a snippet.
MARKDOWN_NOISE = re.compile(r"\*\*|`|^\s*(?:[-*+]|\d+\.)\s+")
MARKDOWN_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")


@dataclass
class SummaryHeader:
    """The metadata block summarize writes at the top of summary.md."""

    name: Optional[str]
    fields: dict = field(default_factory=dict)
    #: Index of the first line after the `**Field:**` lines.
    end_line: int = 0


def parse_summary_header(text: str) -> SummaryHeader:
    lines = text.splitlines()
    i = 0
    name = None
    if lines and lines[0].startswith("# "):
        name = lines[0][2:].strip() or None
        i = 1
    while i < len(lines) and not lines[i].strip():
        i += 1

    fields = {}
    while i < len(lines):
        match = HEADER_FIELD.match(lines[i])
        if not match:
            break
        fields[match.group(1).strip()] = match.group(2).strip()
        i += 1
    return SummaryHeader(name=name, fields=fields, end_line=i)


def load_json(path: Path) -> Optional[Any]:
    """Parse a JSON file, or None when it is missing or unreadable."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def iter_firm_dirs(output_dir: Path, category_ids: Iterable[str]) -> Iterator[tuple[str, Path]]:
    """Yield (category_id, firm_dir) for every firm folder, in a stable order."""
    for category_id in category_ids:
        category_path = output_dir / category_id
        if not category_path.is_dir():
            continue
        for firm_dir in sorted(category_path.iterdir()):
            if firm_dir.is_dir():
                yield category_id, firm_dir


def resolve_firm_dir(category_path: Path, firm_name: str) -> Optional[Path]:
    """The folder `firm_name` names inside `category_path`, or None.

    `firm_name` comes from a URL, so it must resolve to a direct child folder:
    "..", separators and symlinks that point elsewhere are all refused.
    """
    if not firm_name or firm_name in {".", ".."}:
        return None
    if any(ch in firm_name for ch in ("/", "\\", "\x00")):
        return None
    try:
        base = category_path.resolve(strict=True)
        candidate = (base / firm_name).resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        return None
    if candidate.parent != base or not candidate.is_dir():
        return None
    return candidate


def summary_body(text: str, segmentation: Optional[dict] = None, taxonomy: Optional[dict] = None) -> str:
    """summary.md without its header, AI notice, 세분류 block and sources: the prose."""
    header = parse_summary_header(text)
    lines = [line for line in text.splitlines()[header.end_line:] if not line.startswith(NOTICE_MARKER)]
    if SOURCES_HEADING in lines:
        lines = lines[: lines.index(SOURCES_HEADING)]
    body = "\n".join(lines)
    if SEGMENTATION_HEADING not in body:
        return body.strip()

    block = seg.segmentation_markdown(segmentation, taxonomy) if segmentation and taxonomy else None
    if block and block in body:
        return body.replace(block, "", 1).strip()

    # A hand-edited block, or no record to rebuild it from: drop everything
    # from its heading up to the next heading.
    lines = body.splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip() == SEGMENTATION_HEADING)
    end = next(
        (i for i in range(start + 1, len(lines)) if lines[i].startswith("#")),
        len(lines),
    )
    return "\n".join(lines[:start] + lines[end:]).strip()


def with_notice(text: str) -> str:
    """summary.md text with the AI notice after its header, added only if missing.

    For summaries written before the notice existed, so anything that copies
    them elsewhere (Supabase, exports) still carries the label.
    """
    if NOTICE_MARKER in text:
        return text
    header = parse_summary_header(text)
    lines = text.splitlines()
    rest = lines[header.end_line:]
    while rest and not rest[0].strip():
        rest.pop(0)
    joined = "\n".join(lines[: header.end_line] + ["", AI_NOTICE_MARKDOWN, ""] + rest)
    return joined + "\n" if text.endswith("\n") else joined


def plain_text(markdown: str) -> str:
    """Flatten Markdown prose to one line: no headings, tables or emphasis."""
    parts = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "|")):
            continue
        stripped = MARKDOWN_LINK.sub(r"\1", stripped)
        parts.append(MARKDOWN_NOISE.sub("", stripped).strip())
    return " ".join(part for part in parts if part)


def snippet(text: str, needle: str = "", width: int = 90) -> str:
    """About `width` characters of `text`, centred on `needle` when it occurs."""
    position = text.casefold().find(needle.casefold()) if needle else -1
    if position < 0 or len(text) <= width:
        start = 0
    else:
        start = max(0, min(position - width // 3, len(text) - width))
    end = start + width
    out = text[start:end].strip()
    if start > 0:
        out = "…" + out
    if end < len(text):
        out += "…"
    return out


def firm_record(category_id: str, category_name: str, firm_dir: Path) -> dict:
    """One flat row describing a firm folder, for CSV export."""
    header = parse_summary_header(read_text(firm_dir / "summary.md"))
    webpage = load_json(firm_dir / "webpage.json")
    webpage = webpage if isinstance(webpage, dict) else {}
    segmentation = load_json(firm_dir / "segmentation.json")
    segmentation = segmentation if isinstance(segmentation, dict) else None

    url = webpage.get("url") or ""
    record = {
        "firm_name": header.name or firm_dir.name,
        "address": header.fields.get("Address", ""),
        "category_id": category_id,
        "category": category_name,
        "webpage": url,
        "webpage_confidence": (webpage.get("confidence") or "") if url else "",
        "segmented": segmentation is not None,
    }
    record.update(seg.segmentation_columns(segmentation or {}))
    return record


def collect_records(output_dir: Path, categories: list) -> list[dict]:
    """A row per firm folder across every configured category."""
    names = {cat["id"]: cat.get("name", cat["id"]) for cat in categories if cat.get("id")}
    return [
        firm_record(category_id, names[category_id], firm_dir)
        for category_id, firm_dir in iter_firm_dirs(output_dir, names)
    ]


def insert_segmentation_block(text: str, block: str) -> str:
    """Place a 세분류 block between the summary.md header (and AI notice) and its body.

    Mirrors the layout summarize writes: header lines, the notice, the block,
    then the body, separated by blank lines.
    """
    header = parse_summary_header(text)
    lines = text.splitlines()
    head = lines[: header.end_line]
    rest = lines[header.end_line:]
    while rest and not rest[0].strip():
        rest.pop(0)
    notice = []
    if rest and rest[0].startswith(NOTICE_MARKER):
        notice = ["", rest.pop(0)]
        while rest and not rest[0].strip():
            rest.pop(0)

    new_lines = head + notice + [""] + block.splitlines() + [""] + rest
    joined = "\n".join(new_lines)
    return joined + "\n" if text.endswith("\n") else joined


def set_header_field(text: str, name: str, value: str) -> str:
    """Rewrite one `**Name:** value` header line, leaving the body untouched."""
    header = parse_summary_header(text)
    lines = text.splitlines()
    for index in range(header.end_line):
        match = HEADER_FIELD.match(lines[index])
        if match and match.group(1).strip() == name:
            lines[index] = f"**{name}:** {value}"
            break
    else:
        return text
    joined = "\n".join(lines)
    return joined + "\n" if text.endswith("\n") else joined
