#!/usr/bin/env python3
"""Tests for the segmentation backfill (firm-segment) and the CSV export.

Both read the per-firm result folders, so each test builds a small results
tree in tmp_path and stubs the LLM provider.
"""

import csv
import io
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from firm_analyzer.core import export, resegment  # noqa: E402
from firm_analyzer.core import segmentation as seg  # noqa: E402
from firm_analyzer.core.results import (  # noqa: E402
    SEGMENTATION_HEADING,
    collect_records,
    insert_segmentation_block,
    parse_summary_header,
    set_header_field,
)
from firm_analyzer.llm import LLMError  # noqa: E402

CATEGORIES = [
    {"id": "ai_ml", "name": "AI/Machine Learning"},
    {"id": "healthcare", "name": "Healthcare/Bio"},
    {"id": "general", "name": "General"},
]

SUMMARY = """# {name}

**Address:** 서울특별시 강남구
**Category:** General
**Official Webpage:** [https://example.com](https://example.com)

### {name}

- 사업 영역: 신약 개발
"""

BIO = {"segmentation": {"sector": "bio_health", "subsector": "drug_discovery",
                        "confidence": {"sector": "high"}}}
SOFTWARE = {"segmentation": {"sector": "ict_software", "subsector": "data_ai_solution"}}


def make_firm(root, category, name, search=True, segmentation=None, webpage=None):
    firm_dir = root / category / name
    firm_dir.mkdir(parents=True)
    (firm_dir / "summary.md").write_text(SUMMARY.format(name=name), encoding="utf-8")
    if search:
        (firm_dir / "raw_search.json").write_text(
            json.dumps({"results": [{"title": name, "url": "https://example.com", "content": "c"}]}),
            encoding="utf-8",
        )
    if segmentation is not None:
        (firm_dir / "segmentation.json").write_text(json.dumps(segmentation), encoding="utf-8")
    if webpage is not None:
        (firm_dir / "webpage.json").write_text(json.dumps(webpage), encoding="utf-8")
    return firm_dir


class StubProvider:
    label = "Stub"
    model = "stub-1"

    def __init__(self, answers):
        self.answers = answers
        self.calls = []

    def api_key(self):
        return "stub-key"

    def complete_json(self, prompt, system=None, max_output_tokens=None):
        for name, answer in self.answers.items():
            if f"업체명: {name}" in prompt:
                self.calls.append(name)
                if isinstance(answer, Exception):
                    raise answer
                return answer
        raise AssertionError("prompt named no known firm")


@pytest.fixture
def results(tmp_path):
    return tmp_path / "results"


@pytest.fixture
def run_segment(monkeypatch, results):
    monkeypatch.setattr(resegment, "load_config", lambda: {"categories": CATEGORIES})

    def run(answers, *argv):
        provider = StubProvider(answers)
        monkeypatch.setattr(resegment, "get_provider", lambda *a, **k: provider)
        monkeypatch.setattr(sys, "argv", ["firm-segment", "-o", str(results), "--delay", "0", *argv])
        resegment.main()
        return provider

    return run


# --- summary.md helpers ------------------------------------------------------

def test_parse_summary_header():
    header = parse_summary_header(SUMMARY.format(name="알파"))
    assert header.name == "알파"
    assert header.fields["Address"] == "서울특별시 강남구"
    assert header.fields["Category"] == "General"
    assert header.end_line == 5


def test_insert_block_sits_between_header_and_body():
    text = insert_segmentation_block(SUMMARY.format(name="알파"), "## 세분류 (Segmentation)\n\n| a |")
    lines = text.splitlines()
    assert lines[4].startswith("**Official Webpage:**")
    assert lines[5:9] == ["", "## 세분류 (Segmentation)", "", "| a |"]
    assert lines[9:11] == ["", "### 알파"]
    assert text.endswith("- 사업 영역: 신약 개발\n")


def test_set_header_field_leaves_the_body_alone():
    text = SUMMARY.format(name="알파") + "\n**Category:** 본문 속 같은 형태의 줄\n"
    updated = set_header_field(text, "Category", "Healthcare/Bio")
    assert "**Category:** Healthcare/Bio" in updated
    assert "**Category:** 본문 속 같은 형태의 줄" in updated


# --- firm-segment --------------------------------------------------------------

def test_backfill_segments_unsegmented_firms_only(run_segment, results):
    make_firm(results, "general", "알파")
    make_firm(results, "general", "베타", segmentation={"sector": "finance"})
    make_firm(results, "general", "감마", search=False)

    provider = run_segment({"알파": BIO})

    assert provider.calls == ["알파"]
    saved = json.loads((results / "general" / "알파" / "segmentation.json").read_text())
    assert saved["sector"] == "bio_health"
    summary = (results / "general" / "알파" / "summary.md").read_text()
    assert summary.count(SEGMENTATION_HEADING) == 1
    assert summary.index(SEGMENTATION_HEADING) < summary.index("### 알파")
    # Without --relocate the firm stays where it was.
    assert "**Category:** General" in summary


def test_relocate_moves_firm_to_the_mapped_category(run_segment, results):
    make_firm(results, "general", "알파")
    run_segment({"알파": BIO}, "--relocate")

    moved = results / "healthcare" / "알파"
    assert moved.is_dir()
    assert not (results / "general" / "알파").exists()
    assert "**Category:** Healthcare/Bio" in (moved / "summary.md").read_text()


def test_relocate_never_overwrites_an_existing_folder(run_segment, results):
    make_firm(results, "general", "알파")
    make_firm(results, "healthcare", "알파", segmentation={"sector": "bio_health"})
    run_segment({"알파": BIO}, "--relocate", "--category", "general")

    assert (results / "general" / "알파" / "segmentation.json").exists()


def test_force_replaces_the_previous_block(run_segment, results):
    firm_dir = make_firm(results, "general", "알파")
    run_segment({"알파": BIO})
    run_segment({"알파": SOFTWARE}, "--force")

    summary = (firm_dir / "summary.md").read_text()
    assert summary.count(SEGMENTATION_HEADING) == 1
    assert "`ict_software`" in summary
    assert "`bio_health`" not in summary


def test_one_failure_does_not_stop_the_backfill(run_segment, results, capsys):
    make_firm(results, "general", "알파")
    make_firm(results, "general", "베타")
    run_segment({"알파": LLMError("500 internal"), "베타": SOFTWARE})

    assert not (results / "general" / "알파" / "segmentation.json").exists()
    assert (results / "general" / "베타" / "segmentation.json").exists()
    assert "1 segmented, 1 failed." in capsys.readouterr().out


def test_quota_error_stops_the_backfill(run_segment, results, capsys):
    # Folders are visited in sorted order: 가나 first, then 다라.
    make_firm(results, "general", "가나")
    make_firm(results, "general", "다라")
    with pytest.raises(SystemExit) as exit_info:
        run_segment({"가나": LLMError("RESOURCE_EXHAUSTED: quota exceeded"), "다라": BIO})
    assert exit_info.value.code == 1
    assert not (results / "general" / "다라" / "segmentation.json").exists()
    assert "0 segmented, 0 failed." in capsys.readouterr().out


def test_dry_run_writes_nothing(run_segment, results, capsys):
    firm_dir = make_firm(results, "general", "알파")
    before = (firm_dir / "summary.md").read_text()
    provider = run_segment({}, "--dry-run")

    assert provider.calls == []
    assert not (firm_dir / "segmentation.json").exists()
    assert (firm_dir / "summary.md").read_text() == before
    assert "1 firm(s) to segment" in capsys.readouterr().out


# --- export --------------------------------------------------------------------

def test_collect_records_reads_every_folder(results):
    taxonomy = seg.load_taxonomy()
    segmentation = seg.validate_segmentation(BIO, taxonomy)
    make_firm(results, "healthcare", "알파", segmentation=segmentation,
              webpage={"url": "https://alpha.example", "confidence": "high"})
    make_firm(results, "general", "베타")
    make_firm(results, "unlisted", "감마")  # not a configured category

    records = {r["firm_name"]: r for r in collect_records(results, CATEGORIES)}
    assert set(records) == {"알파", "베타"}
    alpha = records["알파"]
    assert alpha["category"] == "Healthcare/Bio"
    assert alpha["address"] == "서울특별시 강남구"
    assert alpha["webpage"] == "https://alpha.example"
    assert alpha["segmented"] is True
    assert alpha["sector"] == "bio_health"
    assert records["베타"]["segmented"] is False
    assert records["베타"]["sector"] == ""


def test_export_csv_bytes_is_excel_friendly(results):
    make_firm(results, "general", "알파")
    payload = export.export_csv_bytes(
        {"categories": CATEGORIES, "output": {"directory": str(results)}}
    )
    assert payload.startswith("﻿".encode("utf-8"))
    rows = list(csv.DictReader(io.StringIO(payload.decode("utf-8-sig"))))
    assert rows[0]["firm_name"] == "알파"
    assert "sector" in rows[0]
