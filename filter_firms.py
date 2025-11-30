#!/usr/bin/env python3
"""
Configurable Firm Filter Script

This script filters firms from a CSV based on user-defined configuration.
Filters can be customized via config.json or command-line arguments.
"""

import argparse
import json
import os
import sys

import pandas as pd


def load_config(config_path: str = "config.json") -> dict:
    """Load configuration from JSON file."""
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def filter_by_location(
    df: pd.DataFrame,
    column: str,
    values: list,
    filter_type: str = "contains"
) -> pd.DataFrame:
    """Filter dataframe by location values."""
    if not values:
        return df

    if filter_type == "contains":
        mask = df[column].str.contains("|".join(values), na=False, regex=True)
    elif filter_type == "exact":
        mask = df[column].isin(values)
    elif filter_type == "startswith":
        pattern = "|".join([f"^{v}" for v in values])
        mask = df[column].str.match(pattern, na=False)
    else:
        mask = df[column].str.contains("|".join(values), na=False, regex=True)

    return df[mask]


def main():
    parser = argparse.ArgumentParser(
        description="Filter firms from CSV based on configurable criteria"
    )
    parser.add_argument(
        "-i", "--input",
        default="2025_전문연구요원_인원배정.csv",
        help="Input CSV file path"
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output CSV file path (default: filtered_firms.csv)"
    )
    parser.add_argument(
        "-c", "--config",
        default="config.json",
        help="Configuration file path"
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
    config = load_config(args.config)
    filter_config = config.get("filters", {}).get("location", {})

    # Command-line args override config
    column = args.column or filter_config.get("column", "소재지")
    locations = args.locations or filter_config.get("values", [])
    filter_type = args.filter_type or filter_config.get("type", "contains")

    # Default output filename based on filter
    if args.output:
        output_file = args.output
    elif locations:
        output_file = f"{'_'.join(locations)}_firms.csv"
    else:
        output_file = "filtered_firms.csv"

    # Check input file
    if not os.path.exists(args.input):
        print(f"Error: {args.input} not found.")
        sys.exit(1)

    # Read CSV
    try:
        df = pd.read_csv(args.input)
        print(f"Loaded {len(df)} rows from {args.input}")
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
    filtered_df.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"Filtered {len(filtered_df)} firms.")
    print(f"Saved to {output_file}")

    return filtered_df


if __name__ == "__main__":
    main()
