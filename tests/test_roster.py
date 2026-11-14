#!/usr/bin/env python3
"""Tests for the yearly 인원배정 list: import, compare, activate, and its API."""

import io
import os
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from firm_analyzer.core import pdf_parser_rule, roster  # noqa: E402
from firm_analyzer.web import app as web  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent

LIST_2026 = pd.DataFrame({
    "연번": ["1", "2", "3"],
    "업종구분": ["중소기업", "중소기업", "벤처기업부설연구소"],
    "업체명": ["㈜알파 기업부설연구소", "베타 주식회사", "감마"],
    "소재지": ["서울특별시 강남구", "부산광역시 해운대구", "서울특별시 중구"],
    "26년 배정인원": ["2", "총괄배정", "1"],
    "관할청": ["서울", "부산.울산", "서울"],
})
LIST_2027 = pd.DataFrame({
    "연번": ["1", "2", "3"],
    "업종구분": ["중소기업", "중소기업", "중견기업"],
    "업체명": ["(주)알파 기업부설연구소", "감마", "델타(주)"],
    "소재지": ["서울특별시 강남구", "서울특별시 중구", "경기도 성남시"],
    "27년 배정인원": ["3", "1", "2"],
    "관할청": ["서울", "서울", "경인"],
})


@pytest.fixture
def home(monkeypatch, tmp_path):
    """A throwaway project root with the 2026 list in data/ and an in-memory config."""
    (tmp_path / "data").mkdir()
    LIST_2026.to_csv(tmp_path / "data" / "2026_전문연구요원_인원배정.csv", index=False)
    monkeypatch.setattr(roster, "BASE_DIR", tmp_path)

    config = {"data": {"roster": ""}, "categories": []}
    monkeypatch.setattr(roster, "load_config", lambda: config)
    monkeypatch.setattr(roster, "save_config", lambda new: config.update(new))
    return tmp_path, config


# --- Normalising ----------------------------------------------------------------

def test_yearly_allocation_column_is_renamed_and_aliases_apply():
    assert roster.normalize_columns(["﻿연번", "회사명", "주소", "26년\n배정인원", "업종"]) == [
        "연번", "업체명", "소재지", "배정인원", "업종구분",
    ]


def test_alias_does_not_replace_a_present_canonical_column():
    assert roster.normalize_columns(["업체명", "회사명", "소재지"]) == ["업체명", "회사명", "소재지"]


def test_normalize_drops_blank_header_and_duplicate_rows():
    frame = pd.DataFrame({
        "업체명": ["알파", "  ", "업체명", "알파", "베 타"],
        "소재지": ["서울", "서울", "소재지", "서울", "부산  해운대구"],
    })
    out = roster.normalize_roster(frame)
    assert out["업체명"].tolist() == ["알파", "베 타"]
    assert out["소재지"].tolist() == ["서울", "부산 해운대구"]


def test_normalize_requires_name_and_address():
    with pytest.raises(roster.RosterError, match="소재지"):
        roster.normalize_roster(pd.DataFrame({"업체명": ["알파"]}))


@pytest.mark.parametrize(
    "a, b",
    [
        ("㈜알파 기업부설연구소", "(주)알파 기업부설연구소"),
        ("베타 주식회사", "(주) 베타"),
        ("Tmax R&D Center", "tmax r&d center"),
        ("재단법인 감마연구원", "(재)감마연구원"),
    ],
)
def test_firm_key_matches_the_same_firm_across_spellings(a, b):
    assert roster.firm_key(a) == roster.firm_key(b)


def test_firm_key_keeps_different_firms_apart():
    assert roster.firm_key("알파 연구소") != roster.firm_key("알파 기술연구소")


@pytest.mark.parametrize(
    "filename, columns, expected",
    [
        ("2027_전문연구요원_인원배정.pdf", [], 2027),
        ("인원배정_20271023.pdf", [], 2027),
        ("list.csv", ["업체명", "27년 배정인원"], 2027),
        ("list.csv", ["업체명"], None),
    ],
)
def test_infer_year(filename, columns, expected):
    assert roster.infer_year(filename, columns) == expected


@pytest.mark.parametrize("name", ["../config.yml", "a/b.csv", ".hidden.csv", "notes.txt", "", "x.csv\x00"])
def test_roster_path_refuses_anything_but_a_bare_csv_name(name):
    with pytest.raises(roster.RosterError):
        roster.roster_path(name)


# --- Comparing ------------------------------------------------------------------

def test_compare_reports_new_removed_and_kept_firms():
    diff = roster.compare_frames(
        roster.normalize_roster(LIST_2026), roster.normalize_roster(LIST_2027), "a.csv", "b.csv"
    )
    assert [row["업체명"] for row in diff.added] == ["델타(주)"]
    assert [row["업체명"] for row in diff.removed] == ["베타 주식회사"]
    assert diff.kept == 2  # 알파 (㈜ vs (주)) and 감마
    assert diff.added[0]["배정인원"] == "2"


def test_diff_csv_has_a_bom_and_header_even_when_empty():
    diff = roster.RosterDiff(base="a", target="b")
    body = roster.diff_csv_bytes(diff, "removed")
    assert body.startswith("﻿".encode("utf-8"))
    assert "업체명" in body.decode("utf-8-sig")


# --- The active list ------------------------------------------------------------

def test_newest_year_is_active_by_default(home):
    root, config = home
    LIST_2027.to_csv(root / "data" / "2027_전문연구요원_인원배정.csv", index=False)
    assert roster.active_roster_name(config) == "2027_전문연구요원_인원배정.csv"


def test_configured_list_wins_and_a_missing_one_falls_back(home):
    root, config = home
    LIST_2027.to_csv(root / "data" / "2027_전문연구요원_인원배정.csv", index=False)
    config["data"]["roster"] = "2026_전문연구요원_인원배정.csv"
    assert roster.active_roster_name(config) == "2026_전문연구요원_인원배정.csv"
    config["data"]["roster"] = "gone.csv"
    assert roster.active_roster_name(config) == "2027_전문연구요원_인원배정.csv"


def test_list_skips_the_filter_output_and_non_lists(home):
    root, config = home
    LIST_2026.to_csv(root / "data" / "filtered_firms.csv", index=False)
    pd.DataFrame({"a": [1]}).to_csv(root / "data" / "other.csv", index=False)
    names = [info.name for info in roster.list_rosters(config)]
    assert names == ["2026_전문연구요원_인원배정.csv"]


# --- Importing ------------------------------------------------------------------

def test_import_cp949_csv_compares_with_the_previous_list_and_activates(home, tmp_path_factory):
    root, config = home
    upload = tmp_path_factory.mktemp("upload") / "명단.csv"
    LIST_2027.to_csv(upload, index=False, encoding="cp949")  # how 정부 CSVs often arrive

    result = roster.import_roster(upload, year=2027, config=config)

    written = pd.read_csv(root / "data" / "2027_전문연구요원_인원배정.csv", dtype=str)
    assert list(written.columns) == ["연번", "업종구분", "업체명", "소재지", "배정인원", "관할청"]
    assert result.previous == "2026_전문연구요원_인원배정.csv"
    assert result.diff.counts() == {"added": 1, "removed": 1, "kept": 2}
    assert config["data"]["roster"] == "2027_전문연구요원_인원배정.csv"
    assert result.roster.active and result.warnings == []


def test_import_refuses_to_overwrite_without_asking(home, tmp_path_factory):
    _, config = home
    upload = tmp_path_factory.mktemp("upload") / "2026.csv"
    LIST_2027.to_csv(upload, index=False)
    with pytest.raises(roster.RosterError, match="이미"):
        roster.import_roster(upload, config=config)
    assert roster.import_roster(upload, overwrite=True, activate=False, config=config).roster.rows == 3
    assert config["data"]["roster"] == ""


def test_import_warns_when_rows_look_missing(home, tmp_path_factory):
    _, config = home
    upload = tmp_path_factory.mktemp("upload") / "2028.csv"
    LIST_2027.assign(연번=["1", "2", "9"]).to_csv(upload, index=False)
    result = roster.import_roster(upload, config=config)
    assert any("연번" in warning for warning in result.warnings)


def test_import_without_a_year_anywhere_asks_for_one(home, tmp_path_factory):
    _, config = home
    upload = tmp_path_factory.mktemp("upload") / "list.csv"
    LIST_2026.rename(columns={"26년 배정인원": "배정인원"}).to_csv(upload, index=False)
    with pytest.raises(roster.RosterError, match="연도"):
        roster.import_roster(upload, config=config)


# --- PDF extraction --------------------------------------------------------------

@pytest.mark.parametrize(
    "row, expected",
    [
        (["연번", "업종구분", "업체명", "소재지", "26년\n배정인원", "관할청"], True),
        (["번호", "회사명", "주소"], True),
        # Data rows that mention 기업 and 회사 used to be read as headers.
        (["936", "중소기업", "농업회사법인 만나씨이에이(주) 기업부설연구소", "충청북도", "총괄배정", "충북"], False),
        (["", "중소기업", "주식회사 도브러너 보안기술연구소", "서울특별시 강남구 논현로", "", "서울"], False),
    ],
)
def test_is_header_row(row, expected):
    assert pdf_parser_rule.is_header_row(row) is expected


def test_match_columns_ignores_empty_header_cells_and_wrapped_text():
    mapping = pdf_parser_rule.match_columns(["연번", "", "업체명", "26년\n배정인원"], pdf_parser_rule.DEFAULT_COLUMNS)
    assert mapping == {0: "연번", 2: "업체명", 3: "배정인원"}


@pytest.mark.skipif(
    not (REPO_ROOT / "data" / "2026_전문연구요원_인원배정.pdf").exists(), reason="2026 PDF not present"
)
def test_the_2026_pdf_parses_every_row():
    rows = pdf_parser_rule.extract_rows(
        str(REPO_ROOT / "data" / "2026_전문연구요원_인원배정.pdf"), verbose=False
    )
    assert [int(row[0]) for row in rows] == list(range(1, 1006))
    assert all(row[4] for row in rows), "배정인원 must be filled for every row"


# --- API --------------------------------------------------------------------------

@pytest.fixture
def client(home, monkeypatch):
    _, config = home
    monkeypatch.setattr(web, "load_config", lambda: config)
    web.app.config["TESTING"] = True
    return web.app.test_client()


def upload(client, frame, filename="2027_전문연구요원_인원배정.csv", **fields):
    body = frame.to_csv(index=False).encode("utf-8")
    data = {"file": (io.BytesIO(body), filename), **fields}
    return client.post("/api/rosters/import", data=data, content_type="multipart/form-data")


def test_api_lists_rosters_with_the_active_one(client):
    data = client.get("/api/rosters").get_json()
    assert data["active"] == "2026_전문연구요원_인원배정.csv"
    assert data["rosters"][0]["rows"] == 3 and data["rosters"][0]["active"] is True


def test_api_import_returns_the_diff_and_switches_the_active_list(client):
    response = upload(client, LIST_2027)
    data = response.get_json()
    assert response.status_code == 200, data
    assert data["diff"]["counts"] == {"added": 1, "removed": 1, "kept": 2}
    assert data["activated"] is True
    assert client.get("/api/rosters").get_json()["active"] == "2027_전문연구요원_인원배정.csv"


@pytest.mark.parametrize(
    "filename, fields, message",
    [
        ("evil.exe", {}, "PDF 또는 CSV"),
        ("2027.csv", {"method": "magic"}, "Unknown method"),
        ("2027.csv", {"method": "llm", "provider": "evil; rm"}, "Unknown provider"),
        ("2026.csv", {}, "이미"),
        ("2027.csv", {"year": "abc"}, "연도"),
    ],
)
def test_api_import_rejects_bad_requests(client, filename, fields, message):
    response = upload(client, LIST_2027, filename=filename, **fields)
    assert response.status_code == 400
    assert message in response.get_json()["error"]


def test_api_compare_and_csv_download(client):
    upload(client, LIST_2027, activate="false")
    params = "base=2026_전문연구요원_인원배정.csv&target=2027_전문연구요원_인원배정.csv"
    data = client.get(f"/api/rosters/compare?{params}").get_json()
    assert data["counts"] == {"added": 1, "removed": 1, "kept": 2}

    csv = client.get(f"/api/rosters/compare.csv?{params}&part=removed")
    assert csv.status_code == 200
    assert "베타 주식회사" in csv.data.decode("utf-8-sig")
    assert "filename*=UTF-8''" in csv.headers["Content-Disposition"]


def test_api_activate_and_download(client):
    upload(client, LIST_2027, activate="false")
    response = client.post("/api/rosters/active", json={"name": "2027_전문연구요원_인원배정.csv"})
    assert response.status_code == 200
    assert client.get("/api/rosters/2027_전문연구요원_인원배정.csv/download").status_code == 200


@pytest.mark.parametrize("name", ["../config.yml", "filtered_firms.csv", "nope.csv"])
def test_api_refuses_unknown_or_path_like_names(client, name):
    assert client.post("/api/rosters/active", json={"name": name}).status_code == 400
    assert client.get(f"/api/rosters/compare?base={name}&target=x.csv").status_code == 400


def test_unknown_api_paths_stay_json_404_not_the_spa(client):
    response = client.get("/api/nope")
    assert response.status_code == 404
    assert response.is_json


def test_client_routes_fall_back_to_the_built_frontend(client, monkeypatch, tmp_path_factory):
    dist = tmp_path_factory.mktemp("dist")
    (dist / "index.html").write_text('<div id="root"></div>', encoding="utf-8")
    (dist / "assets").mkdir()
    (dist / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    monkeypatch.setattr(web, "FRONTEND_DIST", dist)

    assert b'id="root"' in client.get("/rosters").data
    assert client.get("/assets/app.js").data == b"console.log(1)"
    assert b'id="root"' in client.get("/../../etc/passwd").data  # never a file outside dist


def test_without_a_build_the_root_explains_how_to_build_it(client, monkeypatch, tmp_path):
    monkeypatch.setattr(web, "FRONTEND_DIST", tmp_path / "missing")
    assert b"npm run build" in client.get("/").data
