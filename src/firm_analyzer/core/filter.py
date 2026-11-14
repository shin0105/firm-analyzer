#!/usr/bin/env python3
"""
Configurable firm filter: the first pipeline stage.

Reads the active 인원배정 list (see firm_analyzer.core.roster), keeps the rows
that pass the location filter in config.yml, and writes data/filtered_firms.csv,
which summarize reads.
"""

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

from firm_analyzer.config import BASE_DIR, FILTERED_CSV, load_config
from firm_analyzer.core.roster import active_roster_path


def filter_by_location(
    df: pd.DataFrame,
    column: str,
    values: list,
    filter_type: str = "contains"
) -> pd.DataFrame:
    """Filter dataframe by location values."""
    if not values:
        return df

    # Escape regex special characters to prevent injection
    escaped_values = [re.escape(v) for v in values]

    if filter_type == "contains":
        mask = df[column].str.contains("|".join(escaped_values), na=False, regex=True)
    elif filter_type == "exact":
        mask = df[column].isin(values)
    elif filter_type == "startswith":
        pattern = "|".join([f"^{v}" for v in escaped_values])
        mask = df[column].str.match(pattern, na=False)
    else:
        mask = df[column].str.contains("|".join(escaped_values), na=False, regex=True)

    return df[mask]


def main():
    parser = argparse.ArgumentParser(
        description="Filter firms from CSV based on configurable criteria"
    )
    parser.add_argument(
        "-i", "--input",
        default=None,
        help="Input CSV (default: the active 인원배정 list, see `firm-roster list`)"
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output CSV file path (default: data/filtered_firms.csv, which summarize reads)"
    )
    parser.add_argument(
        "-l", "--locations",
        nargs="+",
        default=None,
        help="Location filter values (overrides config)"
    )
    parser.add_argument(
        "--column",
        default=None,
        help="Column name to filter on (overrides config)"
    )
    parser.add_argument(
        "--filter-type",
        choices=["contains", "exact", "startswith"],
        default=None,
        help="Filter type (overrides config)"
    )

    args = parser.parse_args()

    # Load configuration
    config = load_config()
    filter_config = config.get("filters", {}).get("location", {})

    # Command-line args override config. A filter switched off in config.yml
    # contributes no values, so every row passes unless -l is given.
    column = args.column or filter_config.get("column", "소재지")
    config_values = filter_config.get("values", []) if filter_config.get("enabled", True) else []
    locations = args.locations or config_values
    filter_type = args.filter_type or filter_config.get("type", "contains")

    # One fixed default, not a name derived from the filter values: summarize
    # reads FILTERED_CSV, and the web UI runs the two stages back to back.
    if args.output:
        output_file = Path(args.output).expanduser()
        if not output_file.is_absolute():
            output_file = BASE_DIR / "data" / output_file
    else:
        output_file = FILTERED_CSV

    if args.input:
        input_path = _resolve(args.input, BASE_DIR)
    else:
        input_path = active_roster_path(config)
        if input_path is None:
            print("Error: no 인원배정 list in data/. Import one with `firm-roster import <file>`.")
            sys.exit(1)
    if not input_path.exists():
        print(f"Error: {input_path} not found.")
        sys.exit(1)

    # Read CSV
    try:
        df = pd.read_csv(input_path)
        print(f"Loaded {len(df)} rows from {input_path}")
    except Exception as e:
        print(f"Error reading CSV: {e}")
        sys.exit(1)

    # Check column exists
    if column not in df.columns:
        print(f"Error: Column '{column}' not found in CSV.")
        print("Available columns:", list(df.columns))
        sys.exit(1)

    # Apply filter
    if locations:
        filtered_df = filter_by_location(df, column, locations, filter_type)
        print(f"Filter: {column} {filter_type} {locations}")
    else:
        filtered_df = df
        print("No filter applied, using all rows")

    # Save result
    output_file.parent.mkdir(parents=True, exist_ok=True)
    filtered_df.to_csv(str(output_file), index=False, encoding="utf-8")
    print(f"Filtered {len(filtered_df)} firms.")
    print(f"Saved to {output_file}")

    return filtered_df


def _resolve(path: str, base: Path) -> Path:
    """An absolute path as-is; a relative one under `base`, else from the cwd."""
    candidate = Path(path).expanduser()
    if candidate.is_absolute() or not (base / candidate).exists():
        return candidate
    return base / candidate


if __name__ == "__main__":
    main()
