#!/usr/bin/env python3
"""Tests for the Flask API, through its test client.

Covers the export endpoint and the input checks that keep URL segments and
upload names from reaching the filesystem unchecked.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from firm_analyzer.web import app as web  # noqa: E402

CATEGORIES = [
    {"id": "ai_ml", "name": "AI/Machine Learning", "color": "#9C27B0"},
    {"id": "general", "name": "General", "color": "#607D8B"},
]


@pytest.fixture
def results(tmp_path):
    firm_dir = tmp_path / "results" / "ai_ml" / "알파"
    firm_dir.mkdir(parents=True)
    (firm_dir / "summary.md").write_text("# 알파\n\n**Address:** 서울\n\n본문\n", encoding="utf-8")
    (firm_dir / "segmentation.json").write_text(json.dumps({"sector": "ict_software"}))
    (tmp_path / "results" / "general" / "베타").mkdir(parents=True)
    return tmp_path / "results"


@pytest.fixture
def client(monkeypatch, results):
    config = {
        "app": {"data_source": "csv"},
        "categories": CATEGORIES,
        "output": {"directory": str(results)},
    }
    monkeypatch.setattr(web, "load_config", lambda: config)
    web.app.config["TESTING"] = True
    return web.app.test_client()


def test_results_summary_counts_folders(client):
    data = client.get("/api/results/summary").get_json()
    assert data["ai_ml"]["count"] == 1
    assert data["general"]["count"] == 1
    assert data["total"] == 2


def test_results_include_segmentation_and_no_paths(client):
    firms = client.get("/api/results/ai_ml").get_json()["firms"]
    assert firms == [
        {"name": "알파", "summary": "# 알파\n\n**Address:** 서울\n\n본문\n",
         "segmentation": {"sector": "ict_software"}}
    ]


@pytest.mark.parametrize("category", ["nope", "..", "%2E%2E"])
def test_unknown_category_is_rejected(client, category):
    assert client.get(f"/api/results/{category}").status_code == 404


def test_export_csv_downloads_every_firm(client):
    response = client.get("/api/export.csv")
    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert "attachment" in response.headers["Content-Disposition"]
    text = response.data.decode("utf-8-sig")
    lines = text.strip().splitlines()
    assert lines[0].startswith("firm_name,address,category_id")
    assert len(lines) == 3
    assert lines[1].startswith("알파,서울,ai_ml")


@pytest.mark.parametrize(
    "payload",
    [{"limit": "abc"}, {"limit": 0}, {"limit": 10001}, {"provider": "evil; rm -rf"}],
)
def test_summarize_rejects_bad_parameters(client, payload):
    assert client.post("/api/run/summarize", json=payload).status_code == 400


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("보고서.pdf", "보고서.pdf"),
        ("../../../etc/x.pdf", "x.pdf"),
        ("..\\..\\x.pdf", "x.pdf"),
        (".hidden.pdf", None),
        ("notes.txt", None),
        ("..", None),
        ("", None),
    ],
)
def test_safe_upload_name(raw, expected):
    assert web.safe_upload_name(raw) == expected
