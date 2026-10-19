#!/usr/bin/env python3
"""Read the per-firm result folders that summarize writes.

Layout, one folder per firm::

    <output.directory>/<category_id>/<firm>/
        summary.md          # "# name", **Field:** header lines, then the body
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

HEADER_FIELD = re.compile(r"^\*\*([^*]+?):\*\*\s*(.*)$")
SEGMENTATION_HEADING = "## 세분류 (Segmentation)"


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
    """Place a 세분류 block between the summary.md header and its body.

    Mirrors the layout summarize writes: header lines, a blank line, the
    block, a blank line, then the body.
    """
    header = parse_summary_header(text)
    lines = text.splitlines()
    head = lines[: header.end_line]
    rest = lines[header.end_line:]
    while rest and not rest[0].strip():
        rest.pop(0)

    new_lines = head + [""] + block.splitlines() + [""] + rest
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
