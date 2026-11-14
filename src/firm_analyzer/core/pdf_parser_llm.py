#!/usr/bin/env python3
"""Turn a 인원배정 PDF into a CSV using whichever LLM provider is selected.

Every provider-specific detail (native document input vs. a pdfplumber text
pass) lives in firm_analyzer.llm, so this module only owns the extraction
prompt and the JSON -> CSV shaping.
"""

import argparse
import csv
import os
import sys
import tempfile
from typing import Optional

from dotenv import load_dotenv

from firm_analyzer.config import load_config
from firm_analyzer.llm import (
    PDF_PAGES_PER_CHUNK,
    PROVIDER_IDS,
    LLMError,
    get_provider,
    pdf_page_count,
    split_pdf,
)

load_dotenv()

EXTRACTION_PROMPT = """
Extract all the firm/company data from this document and output it as a valid JSON array of objects.
Each object in the array corresponds to a row in a CSV.
You MUST include at least the following two keys for every object:
- "업체명" (Company Name - Required)
- "소재지" (Location/Address - Required)

You may also include other relevant information found in the document as additional keys, such as "업종", "배정인원", "연번", "관할청", etc.

Only output the JSON array, without any markdown blocks (like ```json), just the raw JSON.
""".strip()


def parse_pdf_to_csv(
    pdf_path: str,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    config: Optional[dict] = None,
    pages_per_chunk: int = PDF_PAGES_PER_CHUNK,
) -> str:
    """Parse a PDF into a CSV next to it. Returns the new CSV's filename."""
    rows = extract_pdf_rows(pdf_path, provider, model, config, pages_per_chunk)
    return _write_rows_to_csv(rows, pdf_path)


def extract_pdf_rows(
    pdf_path: str,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    config: Optional[dict] = None,
    pages_per_chunk: int = PDF_PAGES_PER_CHUNK,
) -> list[dict]:
    """The PDF's firm rows as dicts, extracted by the selected LLM.

    Documents longer than `pages_per_chunk` pages are split and extracted in
    several requests, then concatenated. A 28-page 인원배정 table holds far more
    rows than any model will emit in one response, and a single-shot request
    comes back as truncated JSON.
    """
    llm = get_provider(provider, config=config or load_config(), parser_model=model)
    page_count = pdf_page_count(pdf_path)
    print(
        f"Parsing {os.path.basename(pdf_path)} ({page_count} pages) "
        f"with {llm.label} ({llm.parser_model})..."
    )

    if page_count <= pages_per_chunk:
        rows = _extract_rows(llm.pdf_to_json(pdf_path, EXTRACTION_PROMPT))
    else:
        rows = []
        schema: list[str] = []
        with tempfile.TemporaryDirectory() as work_dir:
            chunks = split_pdf(pdf_path, pages_per_chunk, work_dir)
            for index, chunk in enumerate(chunks, start=1):
                print(f"  chunk {index}/{len(chunks)} ({os.path.basename(chunk)})...")
                chunk_rows = _extract_rows(
                    llm.pdf_to_json(chunk, _chunk_prompt(schema))
                )
                print(f"    -> {len(chunk_rows)} rows")
                rows.extend(chunk_rows)

                # Each chunk is an independent request, so without pinning the
                # keys the model renames columns between chunks ("업종구분" in one,
                # "업종" in the next) and the merged CSV ends up half-empty.
                if not schema:
                    schema = list(chunk_rows[0].keys())

    return rows


def _chunk_prompt(schema: list[str]) -> str:
    """The extraction prompt, with the column schema pinned after chunk one."""
    if not schema:
        return EXTRACTION_PROMPT
    keys = ", ".join(f'"{key}"' for key in schema)
    return (
        f"{EXTRACTION_PROMPT}\n\n"
        "This document is being processed in parts. Use EXACTLY these keys for "
        f"every object, in this order, and add no others: {keys}. "
        "If a value is missing on this page, use an empty string."
    )


def _extract_rows(data) -> list[dict]:
    """Normalise one extraction response into a list of row dicts."""
    # Providers in JSON mode sometimes wrap a top-level array in an object,
    # since strict JSON-object modes cannot return a bare array.
    if isinstance(data, dict):
        for value in data.values():
            if isinstance(value, list):
                data = value
                break

    if not isinstance(data, list) or not data:
        raise LLMError("No firm rows were extracted from the document.")

    rows = [row for row in data if isinstance(row, dict)]
    if not rows:
        raise LLMError("Extracted rows were not JSON objects.")
    return rows


def _write_rows_to_csv(rows: list[dict], pdf_path: str) -> str:
    output_filename = pdf_path.replace(".pdf", "_parsed.csv")

    # Gather all unique keys, preserving first-seen order.
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)

    # Ensure the two required columns exist and lead.
    for index, required in enumerate(("업체명", "소재지")):
        if required in keys:
            keys.remove(required)
        keys.insert(index, required)

    with open(output_filename, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Extracted {len(rows)} rows.")
    return os.path.basename(output_filename)


def main():
    parser = argparse.ArgumentParser(
        description="Parse a PDF into CSV using an LLM (OpenAI, Claude or Gemini)."
    )
    parser.add_argument("pdf", help="Path to the PDF file to parse")
    parser.add_argument(
        "--provider",
        choices=PROVIDER_IDS,
        default=None,
        help="LLM provider to use (default: app.llm_provider in config.yml)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override the provider's parser model for this run",
    )
    parser.add_argument(
        "--pages-per-chunk",
        type=int,
        default=PDF_PAGES_PER_CHUNK,
        help=(
            "Pages per extraction request (default: %(default)s). Lower this if "
            "the model runs out of output tokens on dense tables."
        ),
    )
    args = parser.parse_args()

    if not os.path.isfile(args.pdf):
        print(f"Error: {args.pdf} not found.")
        sys.exit(1)

    if args.pages_per_chunk < 1:
        print("Error: --pages-per-chunk must be at least 1.")
        sys.exit(1)

    try:
        output = parse_pdf_to_csv(
            args.pdf,
            provider=args.provider,
            model=args.model,
            pages_per_chunk=args.pages_per_chunk,
        )
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
