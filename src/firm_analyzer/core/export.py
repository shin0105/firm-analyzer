#!/usr/bin/env python3
"""
Export every processed firm to one CSV, rebuilt from the result folders.

The per-category `<category>_firms.csv` files are appended to as summarize
runs and fall out of step with the folders (firms summarized before a column
existed, folders moved by `firm-segment --relocate`, runs that stopped early).
This rebuilds a single table from the folders themselves, with the
segmentation columns, so it always matches what the viewer shows.
"""

import argparse
import io
from pathlib import Path
from typing import Optional

import pandas as pd

from firm_analyzer.config import BASE_DIR, load_config, results_dir
from firm_analyzer.core.results import collect_records

DEFAULT_EXPORT = "firms_export.csv"


def export_frame(config: dict, output_dir: Optional[Path] = None) -> pd.DataFrame:
    """All firm folders as a DataFrame, one row per firm."""
    records = collect_records(output_dir or results_dir(config), config.get("categories", []))
    return pd.DataFrame(records)


def export_csv_bytes(config: dict) -> bytes:
    """The export as UTF-8 CSV with a BOM, so Excel shows Korean correctly."""
    buffer = io.StringIO()
    export_frame(config).to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8-sig")


def main():
    parser = argparse.ArgumentParser(
        description="Export every processed firm, with segmentation columns, to one CSV"
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help=f"Output CSV path (default: <results dir>/{DEFAULT_EXPORT})",
    )
    parser.add_argument(
        "--results-dir",
        default=None,
        help="Results directory to read (default: output.directory in config.yml)",
    )
    args = parser.parse_args()

    config = load_config()
    source = results_dir({"output": {"directory": args.results_dir}} if args.results_dir else config)
    frame = export_frame(config, source)

    output = Path(args.output) if args.output else source / DEFAULT_EXPORT
    if not output.is_absolute():
        output = BASE_DIR / output
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(str(output), index=False, encoding="utf-8-sig")

    segmented = int(frame["segmented"].sum()) if not frame.empty else 0
    print(f"Exported {len(frame)} firms ({segmented} segmented) to {output}")
    if not frame.empty:
        for category, count in frame["category_id"].value_counts().items():
            print(f"  {category}: {count}")


if __name__ == "__main__":
    main()
