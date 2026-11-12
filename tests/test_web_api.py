#!/usr/bin/env python3
"""Tests for the Flask API, through its test client.

Covers the export endpoint, firm search and detail, serving the built
frontend, and the input checks that keep URL segments and upload names from
reaching the filesystem unchecked. The 명단 endpoints are in test_roster.py.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from firm_analyzer.core import segmentation as seg  # noqa: E402
from firm_analyzer.core.results import summary_body  # noqa: E402
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


def make_client(monkeypatch, results, data_source="csv"):
    config = {
        "app": {"data_source": data_source},
        "categories": CATEGORIES,
        "output": {"directory": str(results)},
    }
    monkeypatch.setattr(web, "load_config", lambda: config)
    web.app.config["TESTING"] = True
    return web.app.test_client()


@pytest.fixture
def client(monkeypatch, results):
    return make_client(monkeypatch, results)


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
    # Every row is labelled as AI-generated, so the label survives copying rows out.
    assert lines[0].startswith("notice,firm_name,address,category_id")
    assert len(lines) == 3
    assert all(line.startswith("AI 생성·미검증 참고자료") for line in lines[1:])
    assert ",알파,서울,ai_ml" in lines[1]


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("보고서.pdf", "보고서.pdf"),
        ("2027_명단.CSV", "2027_명단.CSV"),
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


# ---------------------------------------------------------------------------
# /api/firms search and /api/firms/<category>/<firm> detail
# ---------------------------------------------------------------------------

ALPHA = {
    "sector": "ict_software",
    "subsector": "data_ai_solution",
    "verticals": ["ai_ml", "genai_llm"],
    "business_model": "b2b_saas",
    "confidence": {"sector": "high"},
    "evidence": {"sector": "문서 검색 SaaS를 판매"},
    "signals": ["LLM", "SaaS"],
}
BETA = {
    "sector": "semiconductor_hardware",
    "subsector": "fabless_design",
    "verticals": ["chip_design"],
    "business_model": "hardware_product",
    "confidence": {"sector": "low"},
}


def write_firm(root, category, name, body, segmentation=None, address="서울"):
    firm_dir = root / category / name
    firm_dir.mkdir(parents=True)
    text = f"# {name}\n\n**Address:** {address}\n**Category:** {category}\n\n"
    if segmentation is not None:
        taxonomy = seg.load_taxonomy()
        record = seg.validate_segmentation(segmentation, taxonomy)
        (firm_dir / "segmentation.json").write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        text += seg.segmentation_markdown(record, taxonomy) + "\n\n"
    (firm_dir / "summary.md").write_text(text + body, encoding="utf-8")
    return firm_dir


@pytest.fixture
def catalog(tmp_path):
    root = tmp_path / "results"
    write_firm(root, "ai_ml", "알파", "### 알파\n\n- **사업 분야**: LLM 기반 문서 검색 솔루션을 판매합니다.\n", ALPHA)
    write_firm(root, "ai_ml", "감마", "### 감마\n\n- 차량용 반도체 테스트 장비를 유통합니다.\n", address="부산")
    write_firm(root, "general", "베타반도체", "### 베타반도체\n\n팹리스 설계 회사입니다.\n", BETA)
    write_firm(root, "general", "델타", "### 델타\n\n물류 로봇을 만듭니다.\n")
    # A folder for a category the config does not declare is never listed.
    write_firm(root, "secret", "숨김", "### 숨김\n\n반도체\n")
    # Things the detail endpoint must refuse to treat as firms.
    (root / "general" / "notes.txt").write_text("not a firm", encoding="utf-8")
    outside = write_firm(tmp_path / "elsewhere", "x", "외부", "### 외부\n\n유출되면 안 됨\n")
    (root / "general" / "탈출").symlink_to(outside, target_is_directory=True)
    return root


@pytest.fixture
def firms_client(monkeypatch, catalog):
    return make_client(monkeypatch, catalog)


def names(response):
    assert response.status_code == 200, response.get_json()
    return [firm["name"] for firm in response.get_json()["firms"]]


def test_firms_lists_every_configured_category_without_summaries(firms_client):
    data = firms_client.get("/api/firms").get_json()
    # By name across categories. Neither the unconfigured category nor the
    # symlink that points outside the results tree is listed.
    assert [f["name"] for f in data["firms"]] == ["감마", "델타", "베타반도체", "알파"]
    assert data["count"] == data["total"] == 4
    assert all("summary" not in firm for firm in data["firms"])


def test_firm_row_shape(firms_client):
    firms = {f["name"]: f for f in firms_client.get("/api/firms").get_json()["firms"]}
    alpha = firms["알파"]
    assert {k: v for k, v in alpha.items() if k != "snippet"} == {
        "name": "알파",
        "category_id": "ai_ml",
        "category": "AI/Machine Learning",
        "address": "서울",
        "segmented": True,
        "sector": "ict_software",
        "subsector": "data_ai_solution",
        "verticals": ["ai_ml", "genai_llm"],
        "business_model": "b2b_saas",
        "sector_confidence": "high",
    }
    # The snippet is the prose: no header, no 세분류 table, no Markdown.
    assert alpha["snippet"] == "사업 분야: LLM 기반 문서 검색 솔루션을 판매합니다."
    assert firms["감마"]["segmented"] is False
    assert firms["감마"]["sector"] is None and firms["감마"]["verticals"] == []


@pytest.mark.parametrize(
    "query, expected",
    [
        ("q=llm", ["알파"]),            # summary text, case-insensitive
        ("q=델타", ["델타"]),            # firm name
        ("q=부산", ["감마"]),            # header lines are summary text too
        ("q=%20%20", ["감마", "델타", "베타반도체", "알파"]),  # blank = no search
        ("q=없는말", []),
    ],
)
def test_search_matches_name_and_summary(firms_client, query, expected):
    assert names(firms_client.get(f"/api/firms?{query}")) == expected


def test_search_puts_name_matches_first(firms_client):
    # 베타반도체 matches by name; 감마 only mentions 반도체 in its summary.
    assert names(firms_client.get("/api/firms?q=반도체")) == ["베타반도체", "감마"]


def test_search_snippet_centres_on_the_match(monkeypatch, tmp_path):
    body = "가" * 300 + " 희귀단어 " + "나" * 300
    write_firm(tmp_path / "results", "general", "긴회사", body)
    client = make_client(monkeypatch, tmp_path / "results")
    firm = client.get("/api/firms?q=희귀단어").get_json()["firms"][0]
    assert "희귀단어" in firm["snippet"]
    assert firm["snippet"].startswith("…") and firm["snippet"].endswith("…")
    assert len(firm["snippet"]) <= 92


@pytest.mark.parametrize(
    "query, expected",
    [
        ("category=general", ["델타", "베타반도체"]),
        ("sector=ict_software", ["알파"]),
        ("vertical=chip_design", ["베타반도체"]),
        ("vertical=ai_ml", ["알파"]),
        ("business_model=b2b_saas", ["알파"]),
        ("confidence=low", ["베타반도체"]),
        ("segmented=true", ["베타반도체", "알파"]),
        ("segmented=false", ["감마", "델타"]),
        ("category=ai_ml&segmented=false", ["감마"]),
        ("q=반도체&sector=semiconductor_hardware", ["베타반도체"]),
        ("category=ai_ml&sector=semiconductor_hardware", []),
    ],
)
def test_firm_filters(firms_client, query, expected):
    assert names(firms_client.get(f"/api/firms?{query}")) == expected


def test_total_counts_the_scanned_category(firms_client):
    data = firms_client.get("/api/firms?category=ai_ml&segmented=true").get_json()
    assert (data["count"], data["total"]) == (1, 2)


@pytest.mark.parametrize(
    "query, message",
    [
        ("category=nope", "Unknown category: nope"),
        ("category=..", "Unknown category: .."),
        ("category=secret", "Unknown category: secret"),
        ("sector=nope", "Unknown sector: nope"),
        ("sector=data_ai_solution", "Unknown sector: data_ai_solution"),  # a subsector id
        ("vertical=nope", "Unknown vertical: nope"),
        ("business_model=nope", "Unknown business_model: nope"),
        ("confidence=certain", "Unknown confidence: certain"),
        ("segmented=maybe", "segmented must be true or false, not maybe"),
    ],
)
def test_firm_filters_reject_unknown_ids(firms_client, query, message):
    response = firms_client.get(f"/api/firms?{query}")
    assert response.status_code == 400
    assert response.get_json()["error"] == message


def test_firm_detail_returns_summary_and_segmentation(firms_client):
    response = firms_client.get("/api/firms/ai_ml/알파")
    assert response.status_code == 200
    data = response.get_json()
    assert data["name"] == "알파"
    assert (data["category_id"], data["category"], data["address"]) == ("ai_ml", "AI/Machine Learning", "서울")
    assert data["summary"].startswith("# 알파\n")
    assert "## 세분류 (Segmentation)" in data["summary"]
    assert data["segmentation"]["sector"] == "ict_software"


def test_firm_detail_without_segmentation(firms_client):
    data = firms_client.get("/api/firms/general/델타").get_json()
    assert data["segmentation"] is None
    assert "물류 로봇" in data["summary"]


@pytest.mark.parametrize(
    "path",
    [
        "/api/firms/nope/알파",
        "/api/firms/secret/숨김",           # folder exists, category not configured
        "/api/firms/../알파",
        "/api/firms/ai_ml/없는회사",
        "/api/firms/ai_ml/베타반도체",       # lives in another category
        "/api/firms/general/..",
        "/api/firms/general/.",
        "/api/firms/general/%2E%2E",
        "/api/firms/general/..%2Fsecret%2F숨김",
        "/api/firms/general/..%5Csecret%5C숨김",
        "/api/firms/general/notes.txt",     # a file, not a firm folder
        "/api/firms/general/탈출",           # symlink pointing outside results
    ],
)
def test_firm_detail_refuses_anything_but_a_firm_folder(firms_client, path):
    assert firms_client.get(path).status_code == 404


class ExplodingSupabase:
    def __getattr__(self, name):
        raise AssertionError("the firm endpoints must not query Supabase")


def test_firm_endpoints_read_local_folders_under_supabase(monkeypatch, catalog):
    client = make_client(monkeypatch, catalog, data_source="supabase")
    monkeypatch.setattr(web, "supabase_client", ExplodingSupabase())
    assert names(client.get("/api/firms?sector=ict_software")) == ["알파"]
    assert client.get("/api/firms/ai_ml/알파").status_code == 200


def test_summary_body_drops_a_hand_edited_segmentation_block():
    text = (
        "# 회사\n\n**Address:** 서울\n\n"
        "## 세분류 (Segmentation)\n\n| 축 | 값 |\n| --- | --- |\n| 산업 섹터 | 손으로 고침 |\n\n"
        "- sector: 근거\n\n### 회사\n\n본문입니다.\n"
    )
    assert summary_body(text) == "### 회사\n\n본문입니다."
