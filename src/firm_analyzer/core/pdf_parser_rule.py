#!/usr/bin/env python3
"""
Rule-based PDF table to CSV parser, with flexible column mapping.

Reads the tables in a PDF with pdfplumber (no AI, no API key) and writes them
to CSV. Built for the 병무청 전문연구요원 인원배정 lists, but the expected
columns can be changed for other Korean company lists.

Usage:
    # A 인원배정 PDF with the default columns
    firm-parse-pdf --pdf data/2026_전문연구요원_인원배정.pdf

    # Custom column mapping ("source:target" renames a column)
    firm-parse-pdf --pdf data/company_list.pdf -o data/company_list.csv \\
        --columns "번호:Number" "회사명:Company Name" "상세주소:Detail Location"

    # Add a 도시 column derived from the address
    firm-parse-pdf --pdf data/firms.pdf --extract-city-from-location

To import a new yearly list and make it the pipeline's input, use
`firm-roster import` instead, which calls into this module.
"""

import argparse
import csv
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pdfplumber

from firm_analyzer.config import BASE_DIR

#: Columns of a 인원배정 table. "배정인원" matches any year's header
#: ("25년 배정인원", "26년\n배정인원", ...) by substring.
DEFAULT_COLUMNS = ["연번", "업종구분", "업체명", "소재지", "배정인원", "관할청"]

HEADER_KEYWORDS = [
    "번호", "회사", "업체", "기업", "소재지", "주소", "위치", "도시",
    "연번", "업종", "구분", "No", "Number", "Company", "Location",
]


def clean_cell(cell) -> str:
    """A table cell as one line of text: None -> "", runs of whitespace -> one space."""
    if cell is None:
        return ""
    return " ".join(str(cell).split())


def extract_city_from_location(location: str) -> str:
    """
    Extract the city from a Korean address.

    Examples:
        "서울특별시 강남구 테헤란로 123" -> "서울특별시"
        "경기도 수원시 영통구 삼성로 129" -> "수원시"
        "부산광역시 해운대구 센텀중앙로 79" -> "부산광역시"
        "제주특별자치도 제주시 첨단로 242" -> "제주특별자치도"
    """
    if not location:
        return ""

    # Most specific first: 특별자치시 must win over 특별시.
    patterns = [
        r"^([가-힣]+특별자치시)",
        r"^([가-힣]+특별자치도)",
        r"^([가-힣]+특별시)",
        r"^([가-힣]+광역시)",
        r"^([가-힣]+도)\s+([가-힣]+시)",  # 경기도 수원시 -> 수원시
        r"^([가-힣]+시)",
    ]
    for pattern in patterns:
        match = re.search(pattern, location)
        if match:
            if len(match.groups()) > 1 and match.group(2):
                return match.group(2)
            return match.group(1)

    parts = location.split()
    return parts[0] if parts else ""


def parse_column_mapping(column_args: List[str]) -> Tuple[List[str], List[str]]:
    """Split "source:target" (or bare "source") arguments into two lists."""
    source_cols = []
    target_cols = []
    for arg in column_args:
        if ":" in arg:
            source, target = arg.split(":", 1)
            source_cols.append(source.strip())
            target_cols.append(target.strip())
        else:
            source_cols.append(arg.strip())
            target_cols.append(arg.strip())
    return source_cols, target_cols


#: A header cell is short; a long cell that merely mentions "기업" is data.
MAX_HEADER_CELL_LENGTH = 12


def is_header_row(row: List) -> bool:
    """Two or more short cells naming a column, and no all-digit cell.

    Matching keywords against the whole row text is not enough: data rows such
    as "936 | 중소기업 | 농업회사법인 … 기업부설연구소" contain both "기업"
    and "회사", and treating them as headers silently drops the rows above.
    """
    cells = ["".join(clean_cell(cell).split()) for cell in row or []]
    if any(cell.isdigit() for cell in cells):
        return False
    header_like = sum(
        1
        for cell in cells
        if cell
        and len(cell) <= MAX_HEADER_CELL_LENGTH
        and any(keyword.lower() in cell.lower() for keyword in HEADER_KEYWORDS)
    )
    return header_like >= 2


def find_header_row(table: List[List]) -> Tuple[Optional[int], Optional[List[str]]]:
    """The first of the top five rows that looks like a header (see is_header_row)."""
    if not table:
        return None, None
    for idx, row in enumerate(table[:5]):
        if row and is_header_row(row):
            return idx, [clean_cell(cell) for cell in row]
    return None, None


def match_columns(header_row: List[str], expected_columns: List[str]) -> Dict[int, str]:
    """Map header cell index -> expected column name, exact match first, then substring.

    Whitespace is ignored when comparing, so a header PDF cell that wraps
    ("26년\\n배정인원") still matches. Empty header cells are skipped: an
    empty string is a substring of everything and would otherwise claim the
    first expected column.
    """
    column_mapping = {}

    def squash(text: str) -> str:
        return "".join(str(text).split()).lower()

    for idx, col_name in enumerate(header_row):
        col_clean = squash(col_name)
        if not col_clean:
            continue

        for expected in expected_columns:
            if col_clean == squash(expected):
                column_mapping[idx] = expected
                break

        if idx not in column_mapping:
            for expected in expected_columns:
                expected_clean = squash(expected)
                if expected_clean in col_clean or col_clean in expected_clean:
                    column_mapping[idx] = expected
                    break

    return column_mapping


def _location_index(columns: List[str]) -> Optional[int]:
    for i, col in enumerate(columns):
        if "소재지" in col or "주소" in col or "location" in col.lower():
            return i
    return None


def extract_rows(
    pdf_path: str,
    expected_columns: Optional[List[str]] = None,
    extract_city: bool = False,
    min_columns: int = 3,
    verbose: bool = True,
) -> List[List[str]]:
    """Every data row of every table in the PDF, ordered as `expected_columns`.

    With `extract_city`, each row gets one extra trailing cell: the city
    taken from the address column.
    """
    expected_columns = list(expected_columns or DEFAULT_COLUMNS)
    location_idx = _location_index(expected_columns)
    all_rows: List[List[str]] = []

    with pdfplumber.open(pdf_path) as pdf:
        if verbose:
            print(f"Processing PDF with {len(pdf.pages)} pages...")

        for page_num, page in enumerate(pdf.pages, 1):
            for table in page.extract_tables():
                if not table or len(table) < 2:
                    continue

                header_idx, header_row = find_header_row(table)
                if header_row:
                    column_mapping = match_columns(header_row, expected_columns)
                    start_idx = header_idx + 1
                else:
                    # A continuation table without a header: assume column order.
                    column_mapping = dict(enumerate(expected_columns))
                    start_idx = 0

                for row_idx in range(start_idx, len(table)):
                    cells = [clean_cell(cell) for cell in (table[row_idx] or [])]
                    if not any(cells):
                        continue

                    if row_idx > start_idx and is_header_row(cells):
                        continue  # a header repeated inside the table

                    if not column_mapping:
                        if len(cells) >= min_columns:
                            all_rows.append(cells)
                        continue

                    extracted = {
                        name: (cells[idx] if idx < len(cells) else "")
                        for idx, name in column_mapping.items()
                    }
                    output_row = [extracted.get(col, "") for col in expected_columns]

                    if extract_city:
                        location = output_row[location_idx] if location_idx is not None else ""
                        output_row.append(extract_city_from_location(location))

                    if sum(1 for cell in output_row if cell.strip()) >= min_columns:
                        all_rows.append(output_row)

            if verbose:
                print(f"  Page {page_num}/{len(pdf.pages)}: {len(all_rows)} total rows so far")

    return all_rows


def parse_pdf_to_csv_extended(
    pdf_path: str,
    output_csv_path: str,
    expected_columns: Optional[List[str]] = None,
    output_columns: Optional[List[str]] = None,
    extract_city: bool = False,
    min_columns: int = 3,
) -> int:
    """
    Parse a PDF and write its table rows to CSV.

    `expected_columns` are matched against the PDF's header; `output_columns`
    (same length) rename them in the CSV. Returns the number of data rows.
    """
    expected_columns = list(expected_columns or DEFAULT_COLUMNS)
    output_columns = list(output_columns or expected_columns)
    if extract_city and "City" not in output_columns and "도시" not in output_columns:
        output_columns.append("도시")

    rows = extract_rows(pdf_path, expected_columns, extract_city, min_columns)

    with open(output_csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(output_columns)
        for row in rows:
            padded = row + [""] * (len(output_columns) - len(row))
            writer.writerow(padded[: len(output_columns)])

    print(f"\nSuccessfully wrote {len(rows)} rows to {output_csv_path}")
    return len(rows)


def _resolve(path: str) -> Path:
    candidate = Path(path).expanduser()
    return candidate if candidate.is_absolute() else BASE_DIR / candidate


def main():
    parser = argparse.ArgumentParser(
        description="Parse PDF tables to CSV with flexible column mapping (no AI)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --pdf data/2026_전문연구요원_인원배정.pdf
  %(prog)s --pdf data/companies.pdf --output data/companies.csv \\
    --columns "번호" "회사명" "상세주소" "도시"
  %(prog)s --pdf data/firms.pdf --extract-city-from-location
        """,
    )
    parser.add_argument("--pdf", "-p", required=True, help="Path to the input PDF")
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output CSV path (default: the PDF's name with _parsed.csv)",
    )
    parser.add_argument(
        "--columns", "-c",
        nargs="+",
        help='Expected column names (use "source:target" to rename)',
    )
    parser.add_argument(
        "--extract-city-from-location",
        action="store_true",
        help="Add a 도시 column derived from the address column",
    )
    parser.add_argument(
        "--min-columns",
        type=int,
        default=3,
        help="Minimum non-empty cells for a row to count (default: 3)",
    )
    args = parser.parse_args()

    pdf_path = _resolve(args.pdf)
    if not pdf_path.exists():
        raise SystemExit(f"PDF file not found: {pdf_path}")
    output_csv_path = _resolve(args.output) if args.output else pdf_path.with_name(f"{pdf_path.stem}_parsed.csv")

    expected_columns = output_columns = None
    if args.columns:
        expected_columns, output_columns = parse_column_mapping(args.columns)

    num_rows = parse_pdf_to_csv_extended(
        str(pdf_path),
        str(output_csv_path),
        expected_columns=expected_columns,
        output_columns=output_columns,
        extract_city=args.extract_city_from_location,
        min_columns=args.min_columns,
    )

    print("\n✓ Conversion complete!")
    print(f"  Input:  {pdf_path}")
    print(f"  Output: {output_csv_path}")
    print(f"  Rows:   {num_rows}")


if __name__ == "__main__":
    main()
