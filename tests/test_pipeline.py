#!/usr/bin/env python3
"""Tests for the filter -> summarize pipeline.

No network and no API keys: Tavily and the LLM provider are replaced with
stubs, and every file lands in pytest's tmp_path.
"""

import json
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from firm_analyzer.core import filter as firm_filter  # noqa: E402
from firm_analyzer.core import summarize  # noqa: E402
from firm_analyzer.llm import LLMError  # noqa: E402

FIRMS = pd.DataFrame(
    {
        "업체명": ["알파랩", "베타테크", "감마바이오", "델타"],
        "소재지": ["서울특별시 강남구", "서울특별시 마포구", "부산광역시 해운대구", "서울특별시 중구"],
    }
)


@pytest.fixture
def firms_csv(tmp_path):
    path = tmp_path / "firms.csv"
    FIRMS.to_csv(path, index=False)
    return path


def run_main(monkeypatch, module, *argv):
    monkeypatch.setattr(sys, "argv", [module.__name__, *argv])
    return module.main()


# --- filter ------------------------------------------------------------------

def test_filter_output_flag_writes_the_file(monkeypatch, firms_csv, tmp_path):
    """-o used to crash with UnboundLocalError on `Path`."""
    out = tmp_path / "out.csv"
    run_main(monkeypatch, firm_filter, "-i", str(firms_csv), "-o", str(out), "-l", "서울")
    assert list(pd.read_csv(out)["업체명"]) == ["알파랩", "베타테크", "델타"]


def test_filter_respects_a_disabled_location_filter(monkeypatch, firms_csv, tmp_path):
    monkeypatch.setattr(
        firm_filter,
        "load_config",
        lambda: {"filters": {"location": {"enabled": False, "values": ["서울"], "column": "소재지"}}},
    )
    out = tmp_path / "out.csv"
    run_main(monkeypatch, firm_filter, "-i", str(firms_csv), "-o", str(out))
    assert len(pd.read_csv(out)) == len(FIRMS)


def test_filter_default_output_is_what_summarize_reads(monkeypatch, firms_csv, tmp_path, capsys):
    """Run back to back with no arguments, as the web UI does."""
    handoff = tmp_path / "data" / "filtered_firms.csv"
    monkeypatch.setattr(firm_filter, "FILTERED_CSV", handoff)
    monkeypatch.setattr(summarize, "FILTERED_CSV", handoff)
    monkeypatch.setattr(summarize, "load_config", lambda: base_config(tmp_path))

    run_main(monkeypatch, firm_filter, "-i", str(firms_csv), "-l", "서울")
    assert handoff.exists()

    run_main(monkeypatch, summarize, "--dry-run")
    assert "Loaded 3 firms to process." in capsys.readouterr().out


# --- summarize ---------------------------------------------------------------

def base_config(tmp_path, segmentation=False):
    return {
        "categories": [
            {"id": "ai_ml", "name": "AI/Machine Learning"},
            {"id": "healthcare", "name": "Healthcare/Bio"},
            {"id": "general", "name": "General"},
        ],
        "segmentation": {"enabled": segmentation},
        "search": {"find_webpage": False},
        "summary": {},
        "output": {"directory": str(tmp_path / "results"), "create_csv_summary": True},
    }


class StubTavily:
    def __init__(self, api_key=None):
        pass

    def search(self, query, search_depth=None, max_results=None):
        return {"results": [{"title": query, "url": "https://example.com", "content": "본문"}]}


class StubProvider:
    """Answers per firm from a dict; an Exception value is raised instead."""

    label = "Stub"
    model = "stub-1"

    def __init__(self, answers):
        self.answers = answers
        self.calls = []

    def api_key(self):
        return "stub-key"

    def complete_json(self, prompt, system=None, max_output_tokens=None):
        for name, answer in self.answers.items():
            if f"'{name}'" in prompt:
                self.calls.append(name)
                if isinstance(answer, Exception):
                    raise answer
                return answer
        raise AssertionError("prompt named no known firm")


@pytest.fixture
def run_summarize(monkeypatch, firms_csv, tmp_path):
    monkeypatch.setenv("TAVILY_API_KEY", "test")
    monkeypatch.setattr(summarize, "TavilyClient", StubTavily)
    monkeypatch.setattr(summarize.time, "sleep", lambda _: None)

    def run(answers, config=None, *argv):
        provider = StubProvider(answers)
        monkeypatch.setattr(summarize, "get_provider", lambda *a, **k: provider)
        monkeypatch.setattr(summarize, "load_config", lambda: config or base_config(tmp_path))
        run_main(monkeypatch, summarize, "-i", str(firms_csv), *argv)
        return provider

    return run


def ok(category="ai_ml"):
    return {"summary": "요약 본문", "category": category}


def test_one_failing_firm_does_not_stop_the_run(run_summarize, tmp_path, capsys):
    run_summarize(
        {
            "알파랩": ok(),
            "베타테크": LLMError("502 bad gateway"),
            "감마바이오": {"category": "healthcare"},  # no summary -> ValueError
            "델타": ok("general"),
        }
    )
    results = tmp_path / "results"
    assert (results / "ai_ml" / "알파랩" / "summary.md").exists()
    assert (results / "general" / "델타" / "summary.md").exists()
    # Failed firms leave nothing behind, so the next run retries them.
    assert not list(results.glob("*/베타테크"))
    assert not list(results.glob("*/감마바이오"))

    out = capsys.readouterr().out
    assert "2 processed, 0 already done, 2 failed." in out
    assert "베타테크: 502 bad gateway" in out


def test_quota_error_stops_the_run_but_keeps_finished_rows(run_summarize, tmp_path):
    with pytest.raises(SystemExit) as exit_info:
        run_summarize(
            {
                "알파랩": ok(),
                "베타테크": LLMError("429: quota exceeded"),
                "감마바이오": ok("healthcare"),
                "델타": ok(),
            }
        )
    assert exit_info.value.code == 1

    # The CSV is written per firm, so the firm finished before the stop is kept.
    rows = pd.read_csv(tmp_path / "results" / "ai_ml_firms.csv", encoding="utf-8-sig")
    assert list(rows["firm_name"]) == ["알파랩"]
    assert not (tmp_path / "results" / "healthcare").exists()


def test_rerun_skips_finished_firms_and_retries_failed_ones(run_summarize):
    run_summarize({"알파랩": ok(), "베타테크": LLMError("timeout"), "감마바이오": ok(), "델타": ok()})
    second = run_summarize({"알파랩": ok(), "베타테크": ok(), "감마바이오": ok(), "델타": ok()})
    assert second.calls == ["베타테크"]


def test_unknown_or_pathlike_category_lands_in_general(run_summarize, tmp_path):
    run_summarize(
        {
            "알파랩": ok("../../escape"),
            "베타테크": ok("fintech"),
            "감마바이오": ok("healthcare"),
            "델타": ok(),
        }
    )
    results = tmp_path / "results"
    assert (results / "general" / "알파랩").is_dir()
    assert (results / "general" / "베타테크").is_dir()
    assert not (tmp_path / "escape").exists()


def test_segmented_firm_is_filed_by_its_sector(run_summarize, tmp_path):
    answer = {
        "summary": "요약",
        "category": "general",
        "segmentation": {"sector": "bio_health", "subsector": "drug_discovery"},
    }
    run_summarize(
        {"알파랩": answer, "베타테크": answer, "감마바이오": answer, "델타": answer},
        base_config(tmp_path, segmentation=True),
        "--limit", "1",
    )
    firm_dir = tmp_path / "results" / "healthcare" / "알파랩"
    assert json.loads((firm_dir / "segmentation.json").read_text())["sector"] == "bio_health"
    assert "## 세분류 (Segmentation)" in (firm_dir / "summary.md").read_text()


# --- helpers -----------------------------------------------------------------

def test_render_template_tolerates_literal_json_braces():
    template = '{firm_name} 분석. 형식: {"summary": "...", "category": "..."}'
    assert summarize.render_template(template, firm_name="알파") == (
        '알파 분석. 형식: {"summary": "...", "category": "..."}'
    )


def test_render_template_keeps_str_format_escapes():
    assert summarize.render_template("{{x}} {firm_name}", firm_name="알파") == "{x} 알파"


def test_custom_prompt_with_json_example_builds(tmp_path):
    config = base_config(tmp_path)
    config["summary"] = {"custom_prompt": 'Firm {firm_name}. Return {"summary": ""}'}
    prompt = summarize.build_summary_prompt("알파", [], config)
    assert prompt == 'Firm 알파. Return {"summary": ""}'


def test_resolve_category_id():
    ids = {"ai_ml", "general"}
    assert summarize.resolve_category_id("ai_ml", ids) == "ai_ml"
    assert summarize.resolve_category_id(" ai_ml ", ids) == "ai_ml"
    assert summarize.resolve_category_id("../x", ids) == "general"
    assert summarize.resolve_category_id(None, ids) == "general"
    assert summarize.resolve_category_id("x", {"b", "a"}) == "a"
