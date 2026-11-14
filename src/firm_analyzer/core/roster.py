#!/usr/bin/env python3
"""The yearly 전문연구요원 인원배정 list (명단): import, compare, activate.

The 병무청 publishes a new 인원배정 list every year as a PDF. This module turns
that PDF (or a CSV already made from it) into the CSV the pipeline reads,
compares it with the list in use, and records which list the filter step
starts from.

- Each list lives in data/ as `<year>_전문연구요원_인원배정.csv`.
- The active list is `data.roster` in config.yml. When that is unset (or names
  a file that no longer exists) the newest year's list is used.
- Firms are matched across years on a normalised name (`firm_key`), so
  "㈜가우디오랩" and "가우디오랩 주식회사" count as the same firm.

CLI (also `firm-roster`):

    firm-roster list
    firm-roster import data/2027_전문연구요원_인원배정.pdf --year 2027
    firm-roster import list.csv --year 2027 --overwrite
    firm-roster import scan.pdf --year 2027 --method llm --provider gemini
    firm-roster compare 2026_전문연구요원_인원배정.csv 2027_전문연구요원_인원배정.csv
    firm-roster activate 2026_전문연구요원_인원배정.csv
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath
from typing import Optional

import pandas as pd

from firm_analyzer.config import BASE_DIR, FILTERED_CSV, load_config, save_config

ROSTER_STEM = "전문연구요원_인원배정"
ROSTER_NAME = re.compile(rf"^(\d{{4}})_{ROSTER_STEM}\.csv$")
REQUIRED_COLUMNS = ("업체명", "소재지")
#: Canonical column order of an imported list.
CANONICAL_COLUMNS = ("연번", "업종구분", "업체명", "소재지", "배정인원", "관할청")
#: Columns shown when comparing lists.
DISPLAY_COLUMNS = ("업종구분", "업체명", "소재지", "배정인원", "관할청")
#: "25년 배정인원", "2026년 배정인원" -> 배정인원, so lists from different years line up.
YEARLY_ALLOCATION = re.compile(r"^(\d{2}|\d{4})년\s*배정인원$")
#: Header aliases, applied only when the canonical column is missing.
COLUMN_ALIASES = {
    "업체명": ("회사명", "기업명", "업체", "기관명"),
    "소재지": ("주소", "소재지주소", "위치"),
    "업종구분": ("업종", "구분"),
}
#: Legal-form tokens ignored when matching firm names across lists.
LEGAL_FORMS = re.compile(
    r"\((?:주|유|사|재|합|학|의|사단|재단)\)"
    r"|주식회사|유한책임회사|유한회사|사단법인|재단법인|학교법인|의료법인|합자회사|합명회사"
)
MIN_YEAR, MAX_YEAR = 2000, 2100
ENCODINGS = ("utf-8-sig", "cp949")
IMPORT_METHODS = ("rule", "llm")


class RosterError(ValueError):
    """A list that cannot be imported, read or activated. Safe to show users."""


@dataclass
class RosterInfo:
    name: str
    year: Optional[int]
    rows: int
    columns: list
    modified: float
    active: bool = False


@dataclass
class RosterDiff:
    base: str
    target: str
    added: list = field(default_factory=list)
    removed: list = field(default_factory=list)
    kept: int = 0

    def counts(self) -> dict:
        return {"added": len(self.added), "removed": len(self.removed), "kept": self.kept}

    def to_dict(self) -> dict:
        return {"base": self.base, "target": self.target, "counts": self.counts(),
                "added": self.added, "removed": self.removed}


@dataclass
class ImportResult:
    roster: RosterInfo
    previous: Optional[str]
    activated: bool
    diff: Optional[RosterDiff]
    warnings: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "roster": asdict(self.roster),
            "previous": self.previous,
            "activated": self.activated,
            "diff": self.diff.to_dict() if self.diff else None,
            "warnings": self.warnings,
        }


# ---------------------------------------------------------------------------
# Paths and names
# ---------------------------------------------------------------------------

def data_dir() -> Path:
    return BASE_DIR / "data"


def roster_filename(year: int) -> str:
    return f"{year}_{ROSTER_STEM}.csv"


def check_year(year) -> int:
    try:
        value = int(year)
    except (TypeError, ValueError):
        raise RosterError("연도는 숫자여야 합니다 (예: 2027).") from None
    if not MIN_YEAR <= value <= MAX_YEAR:
        raise RosterError(f"연도는 {MIN_YEAR}~{MAX_YEAR} 사이여야 합니다.")
    return value


def infer_year(filename: str, columns: Optional[list] = None) -> Optional[int]:
    """The list's year from its filename ("2027_…") or a "27년 배정인원" header."""
    match = re.search(r"(20\d{2})", PurePosixPath(filename).name)
    if match:
        return int(match.group(1))
    for column in columns or []:
        header = re.match(r"^(\d{2})년\s*배정인원$", " ".join(str(column).split()))
        if header:
            return 2000 + int(header.group(1))
    return None


def roster_path(name: str) -> Path:
    """data/<name> for a bare CSV filename; anything path-like is refused."""
    candidate = PurePosixPath(str(name or "").replace("\\", "/")).name
    if (
        not candidate
        or candidate != name
        or candidate.startswith(".")
        or "\x00" in candidate
        or not candidate.lower().endswith(".csv")
    ):
        raise RosterError("올바르지 않은 명단 파일 이름입니다.")
    return data_dir() / candidate


# ---------------------------------------------------------------------------
# Reading and normalising
# ---------------------------------------------------------------------------

def read_roster(path: Path) -> pd.DataFrame:
    """A list CSV as strings. Government CSVs are often cp949, so both are tried."""
    last_error: Optional[Exception] = None
    for encoding in ENCODINGS:
        try:
            return pd.read_csv(path, dtype=str, keep_default_na=False, encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
        except (pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
            raise RosterError(f"CSV를 읽을 수 없습니다: {exc}") from exc
    raise RosterError(f"CSV 인코딩을 알 수 없습니다 (UTF-8 또는 CP949만 지원): {last_error}")


def _clean_text(value) -> str:
    return " ".join(str(value).split()) if value is not None else ""


def normalize_columns(columns) -> list:
    """Header names with whitespace collapsed and the yearly allocation column renamed."""
    names = []
    for column in columns:
        name = _clean_text(column).lstrip("﻿")
        if YEARLY_ALLOCATION.match(name):
            name = "배정인원"
        names.append(name)
    for canonical, aliases in COLUMN_ALIASES.items():
        if canonical in names:
            continue
        for alias in aliases:
            if alias in names:
                names[names.index(alias)] = canonical
                break
    return names


def normalize_roster(frame: pd.DataFrame) -> pd.DataFrame:
    """Clean an extracted or uploaded list into the pipeline's shape.

    Collapses whitespace, drops blank, repeated-header and duplicate rows,
    and puts the canonical columns first. Raises RosterError when the two
    columns the pipeline needs (업체명, 소재지) are missing.
    """
    frame = frame.copy()
    frame.columns = normalize_columns(frame.columns)
    frame = frame.loc[:, ~pd.Index(frame.columns).duplicated()]
    missing = [c for c in REQUIRED_COLUMNS if c not in frame.columns]
    if missing:
        found = ", ".join(map(str, frame.columns)) or "(없음)"
        raise RosterError(f"필수 열이 없습니다: {', '.join(missing)}. 찾은 열: {found}")

    frame = frame.fillna("").astype(str).apply(lambda col: col.map(_clean_text))
    frame = frame[frame["업체명"] != ""]
    frame = frame[frame["업체명"] != "업체명"]  # a header row repeated mid-table
    frame = frame.drop_duplicates()

    ordered = [c for c in CANONICAL_COLUMNS if c in frame.columns]
    ordered += [c for c in frame.columns if c not in ordered]
    return frame[ordered].reset_index(drop=True)


def firm_key(name: str) -> str:
    """A firm name reduced for matching: legal forms, spaces and punctuation removed."""
    text = unicodedata.normalize("NFKC", str(name or ""))
    text = LEGAL_FORMS.sub("", text)
    return "".join(ch for ch in text if ch.isalnum()).casefold()


def _sanity_warnings(frame: pd.DataFrame) -> list:
    """Signs the extraction lost rows, worth showing before the list is used."""
    warnings = []
    if "연번" in frame.columns:
        numbers = pd.to_numeric(frame["연번"], errors="coerce").dropna()
        if len(numbers) and int(numbers.max()) != len(frame):
            warnings.append(
                f"마지막 연번은 {int(numbers.max())}인데 추출된 행은 {len(frame)}개입니다. "
                "누락되거나 중복된 행이 없는지 원본과 비교해 주세요."
            )
    empty_address = int((frame["소재지"] == "").sum())
    if empty_address:
        warnings.append(f"소재지가 비어 있는 행이 {empty_address}개 있습니다 (위치 필터에서 제외됩니다).")
    return warnings


# ---------------------------------------------------------------------------
# Listing and the active list
# ---------------------------------------------------------------------------

def _header(path: Path) -> list:
    for encoding in ENCODINGS:
        try:
            return list(pd.read_csv(path, nrows=0, encoding=encoding).columns)
        except UnicodeDecodeError:
            continue
        except (pd.errors.ParserError, pd.errors.EmptyDataError, OSError):
            return []
    return []


def is_roster_file(path: Path) -> bool:
    """A CSV in data/ with the columns the filter needs, other than the filter's own output."""
    if not path.is_file() or path.suffix.lower() != ".csv" or path.name.startswith("."):
        return False
    if path.name == FILTERED_CSV.name:
        return False
    columns = normalize_columns(_header(path))
    return all(c in columns for c in REQUIRED_COLUMNS)


def _newest_yearly_roster() -> Optional[str]:
    directory = data_dir()
    if not directory.is_dir():
        return None
    yearly = [
        (int(match.group(1)), path.name)
        for path in directory.iterdir()
        if (match := ROSTER_NAME.match(path.name)) and path.is_file()
    ]
    return max(yearly)[1] if yearly else None


def active_roster_name(config: Optional[dict] = None) -> Optional[str]:
    """The list the filter starts from: `data.roster`, else the newest year's."""
    config = config if config is not None else load_config()
    configured = ((config.get("data") or {}).get("roster") or "").strip()
    if configured:
        try:
            if roster_path(configured).is_file():
                return configured
        except RosterError:
            pass
        print(f"Warning: data.roster '{configured}' not found; using the newest list.", file=sys.stderr)
    return _newest_yearly_roster()


def active_roster_path(config: Optional[dict] = None) -> Optional[Path]:
    name = active_roster_name(config)
    return roster_path(name) if name else None


def roster_info(path: Path, active_name: Optional[str] = None) -> RosterInfo:
    frame = read_roster(path)
    return RosterInfo(
        name=path.name,
        year=infer_year(path.name, list(frame.columns)),
        rows=len(frame),
        columns=normalize_columns(frame.columns),
        modified=path.stat().st_mtime,
        active=path.name == active_name,
    )


def list_rosters(config: Optional[dict] = None) -> list[RosterInfo]:
    """Every list CSV in data/, newest year first."""
    directory = data_dir()
    if not directory.is_dir():
        return []
    active = active_roster_name(config)
    infos = []
    for path in directory.iterdir():
        if not is_roster_file(path):
            continue
        try:
            infos.append(roster_info(path, active))
        except RosterError as exc:
            print(f"Skipping {path.name}: {exc}", file=sys.stderr)
    return sorted(infos, key=lambda info: (-(info.year or 0), info.name))


def set_active_roster(name: str, config: Optional[dict] = None) -> dict:
    """Point `data.roster` at `name` and save config.yml. Returns the new config."""
    path = roster_path(name)
    if not is_roster_file(path):
        raise RosterError(f"명단을 찾을 수 없습니다: {name}")
    config = config if config is not None else load_config()
    config.setdefault("data", {})["roster"] = path.name
    save_config(config)
    return config


# ---------------------------------------------------------------------------
# Comparing
# ---------------------------------------------------------------------------

def _display_rows(frame: pd.DataFrame) -> list:
    columns = [c for c in DISPLAY_COLUMNS if c in frame.columns]
    return frame[columns].to_dict(orient="records")


def compare_frames(base: pd.DataFrame, target: pd.DataFrame, base_name: str = "", target_name: str = "") -> RosterDiff:
    """Firms new in `target`, gone from `base`, and the number in both."""
    base_keys = base["업체명"].map(firm_key)
    target_keys = target["업체명"].map(firm_key)
    base_set, target_set = set(base_keys), set(target_keys)

    added = target[~target_keys.isin(base_set)].drop_duplicates(subset="업체명")
    removed = base[~base_keys.isin(target_set)].drop_duplicates(subset="업체명")
    return RosterDiff(
        base=base_name,
        target=target_name,
        added=_display_rows(added),
        removed=_display_rows(removed),
        kept=len(base_set & target_set),
    )


def compare_rosters(base_name: str, target_name: str) -> RosterDiff:
    frames = []
    for name in (base_name, target_name):
        path = roster_path(name)
        if not is_roster_file(path):
            raise RosterError(f"명단을 찾을 수 없습니다: {name}")
        frames.append(normalize_roster(read_roster(path)))
    return compare_frames(frames[0], frames[1], base_name, target_name)


def diff_csv_bytes(diff: RosterDiff, part: str) -> bytes:
    """`added` or `removed` rows as UTF-8 CSV with a BOM, for Excel."""
    if part not in ("added", "removed"):
        raise RosterError("part는 added 또는 removed여야 합니다.")
    rows = diff.added if part == "added" else diff.removed
    frame = pd.DataFrame(rows, columns=list(DISPLAY_COLUMNS) if not rows else None)
    return frame.to_csv(index=False).encode("utf-8-sig")


# ---------------------------------------------------------------------------
# Importing
# ---------------------------------------------------------------------------

def extract_frame(source: Path, method: str = "rule", provider: Optional[str] = None,
                  config: Optional[dict] = None) -> pd.DataFrame:
    """The raw table in a PDF or CSV, before normalisation."""
    suffix = source.suffix.lower()
    if suffix == ".csv":
        return read_roster(source)
    if suffix != ".pdf":
        raise RosterError("PDF 또는 CSV 파일만 가져올 수 있습니다.")
    if method not in IMPORT_METHODS:
        raise RosterError(f"method는 {' 또는 '.join(IMPORT_METHODS)}여야 합니다.")

    if method == "rule":
        from firm_analyzer.core import pdf_parser_rule

        try:
            rows = pdf_parser_rule.extract_rows(str(source), pdf_parser_rule.DEFAULT_COLUMNS, verbose=False)
        except Exception as exc:  # pdfplumber raises a zoo of types on a damaged file
            raise RosterError(f"PDF를 읽을 수 없습니다: {exc}") from exc
        if not rows:
            raise RosterError(
                "PDF에서 표를 찾지 못했습니다. 스캔 문서라면 'AI로 추출'을 선택해 주세요."
            )
        return pd.DataFrame(rows, columns=pdf_parser_rule.DEFAULT_COLUMNS)

    from firm_analyzer.core import pdf_parser_llm

    return pd.DataFrame(pdf_parser_llm.extract_pdf_rows(str(source), provider=provider, config=config))


def import_roster(
    source: Path,
    year: Optional[int] = None,
    method: str = "rule",
    provider: Optional[str] = None,
    overwrite: bool = False,
    activate: bool = True,
    config: Optional[dict] = None,
) -> ImportResult:
    """Turn a new list into data/<year>_전문연구요원_인원배정.csv.

    The result is compared with the list that was active before the import,
    and, with `activate`, becomes the filter's input. A source PDF is kept next
    to the CSV under the same name, as the record of where the rows came from.
    """
    config = config if config is not None else load_config()
    source = Path(source)
    if not source.is_file():
        raise RosterError(f"파일을 찾을 수 없습니다: {source.name}")

    frame = extract_frame(source, method, provider, config)
    year = check_year(year) if year not in (None, "") else infer_year(source.name, list(frame.columns))
    if year is None:
        raise RosterError("파일 이름에서 연도를 알 수 없습니다. 연도를 입력해 주세요.")

    output = data_dir() / roster_filename(year)
    if output.exists() and not overwrite and output.resolve() != source.resolve():
        raise RosterError(f"{output.name}이(가) 이미 있습니다. 덮어쓰려면 '덮어쓰기'를 선택하세요.")

    roster = normalize_roster(frame)
    if roster.empty:
        raise RosterError("가져올 기업이 없습니다.")

    previous = active_roster_name(config)
    output.parent.mkdir(parents=True, exist_ok=True)
    roster.to_csv(output, index=False, encoding="utf-8")

    if source.suffix.lower() == ".pdf":
        kept_pdf = output.with_suffix(".pdf")
        if kept_pdf.resolve() != source.resolve():
            shutil.copyfile(source, kept_pdf)

    diff = None
    if previous and previous != output.name:
        try:
            diff = compare_rosters(previous, output.name)
        except RosterError as exc:
            print(f"Could not compare with {previous}: {exc}", file=sys.stderr)

    if activate:
        set_active_roster(output.name, config)
    active = output.name if activate else active_roster_name(config)
    return ImportResult(
        roster=roster_info(output, active),
        previous=previous,
        activated=activate,
        diff=diff,
        warnings=_sanity_warnings(roster),
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print_diff(diff: RosterDiff, show: int = 20) -> None:
    counts = diff.counts()
    print(f"{diff.base} -> {diff.target}: +{counts['added']} new, -{counts['removed']} removed, {counts['kept']} in both")
    for label, rows in (("New", diff.added), ("Removed", diff.removed)):
        if not rows:
            continue
        print(f"  {label}:")
        for row in rows[:show]:
            print(f"    {row.get('업체명', '')}  ({row.get('소재지', '')})")
        if len(rows) > show:
            print(f"    … and {len(rows) - show} more")


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Manage the yearly 전문연구요원 인원배정 list")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="Show every list in data/ and which one is active")

    imp = sub.add_parser("import", help="Import a new list from a PDF or CSV")
    imp.add_argument("file", help="The 인원배정 PDF, or a CSV with 업체명 and 소재지 columns")
    imp.add_argument("--year", type=int, default=None, help="List year (default: from the file name)")
    imp.add_argument("--method", choices=IMPORT_METHODS, default="rule",
                     help="PDF extraction: rule (pdfplumber, free) or llm (for scanned PDFs)")
    imp.add_argument("--provider", default=None, help="LLM provider for --method llm")
    imp.add_argument("--overwrite", action="store_true", help="Replace that year's list if it exists")
    imp.add_argument("--no-activate", action="store_true", help="Import without making it the active list")

    cmp_ = sub.add_parser("compare", help="Compare two lists in data/")
    cmp_.add_argument("base")
    cmp_.add_argument("target")
    cmp_.add_argument("--out-dir", default=None, help="Also write added.csv and removed.csv here")

    act = sub.add_parser("activate", help="Make a list in data/ the filter's input")
    act.add_argument("name")

    args = parser.parse_args(argv)
    try:
        if args.command == "list":
            rosters = list_rosters()
            if not rosters:
                print("No lists in data/. Import one with: firm-roster import <file> --year <year>")
            for info in rosters:
                marker = "*" if info.active else " "
                print(f"{marker} {info.name:45} {info.rows:6} firms  year={info.year or '?'}")
        elif args.command == "import":
            source = Path(args.file).expanduser()
            if not source.is_absolute() and not source.exists():
                source = BASE_DIR / source
            result = import_roster(
                source, args.year, args.method, args.provider,
                overwrite=args.overwrite, activate=not args.no_activate,
            )
            print(f"Imported {result.roster.rows} firms into data/{result.roster.name}")
            for warning in result.warnings:
                print(f"Warning: {warning}")
            if result.diff:
                _print_diff(result.diff)
            print(f"Active list: {active_roster_name()}")
        elif args.command == "compare":
            diff = compare_rosters(args.base, args.target)
            _print_diff(diff)
            if args.out_dir:
                out = Path(args.out_dir)
                out.mkdir(parents=True, exist_ok=True)
                for part in ("added", "removed"):
                    (out / f"{part}.csv").write_bytes(diff_csv_bytes(diff, part))
                print(f"Wrote added.csv and removed.csv to {out}")
        elif args.command == "activate":
            set_active_roster(args.name)
            print(f"Active list: {args.name}")
    except RosterError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
