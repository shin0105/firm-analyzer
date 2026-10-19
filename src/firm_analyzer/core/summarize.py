#!/usr/bin/env python3
"""
Configurable Firm Search and Summarize Script

This script searches for firm information, generates summaries, and places each
firm on the multi-axis taxonomy in taxonomy.yml. Categories, prompts, output
format, and which LLM provider to use are all set in config.yml or overridden
on the command line.
"""

import argparse
import json
import os
import re
import sys
import time
from typing import Optional
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from tavily import TavilyClient

from firm_analyzer.config import load_config, BASE_DIR, FILTERED_CSV
from firm_analyzer.core import segmentation as seg
from firm_analyzer.llm import LLMError, LLMProvider, PROVIDER_IDS, get_provider

# Import firm webpage finder module with proper error handling
WEBPAGE_FINDER_AVAILABLE = False
find_firm_webpage = None

try:
    from firm_analyzer.utils.webpage_finder import find_firm_webpage as _find_firm_webpage
    find_firm_webpage = _find_firm_webpage
    WEBPAGE_FINDER_AVAILABLE = True
except ImportError:
    print("Warning: Firm webpage finder module not available")

# Load environment variables
load_dotenv()

DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful assistant that summarizes company information in JSON format."
)


def sanitize_filename(name: str) -> str:
    """Sanitize string for use as filename."""
    return re.sub(r'[\\/*?:"<>|]', "", name)


class QuotaExhausted(RuntimeError):
    """The provider reported a rate limit or spent quota; stop the whole run."""


def render_template(template: str, **values) -> str:
    """Fill `{name}` placeholders in a user-written template.

    str.format is tried first so templates that escape braces as `{{ }}` keep
    working. A template that str.format rejects — typically a custom prompt
    with a literal JSON example in it — falls back to replacing only the known
    placeholders and leaving every other brace alone, instead of crashing the
    run on the first firm.
    """
    try:
        return template.format(**values)
    except (KeyError, IndexError, ValueError):
        pattern = re.compile(r"\{(" + "|".join(map(re.escape, values)) + r")\}")
        return pattern.sub(lambda m: str(values[m.group(1)]), template)


def resolve_category_id(raw: object, valid_ids: set) -> str:
    """Map a model-chosen category onto a configured id.

    The id becomes a directory name, so an invented or path-like value
    ("fintech", "../x") must never reach the filesystem.
    """
    candidate = str(raw or "").strip()
    if candidate in valid_ids:
        return candidate
    if "general" in valid_ids or not valid_ids:
        return "general"
    return sorted(valid_ids)[0]


def append_csv_row(csv_path: Path, row: dict) -> list:
    """Append one firm to a category CSV, aligned to the file's existing header.

    Written per firm rather than at the end of the run, so a run that stops
    part-way still records every firm it finished. Returns the columns the
    existing header lacks (dropped for this append).
    """
    frame = pd.DataFrame([row])
    if not csv_path.exists():
        frame.to_csv(str(csv_path), index=False, encoding="utf-8-sig")
        return []

    existing_columns = list(pd.read_csv(str(csv_path), nrows=0, encoding="utf-8-sig").columns)
    frame.reindex(columns=existing_columns).to_csv(
        str(csv_path), mode="a", header=False, index=False, encoding="utf-8-sig"
    )
    return [c for c in frame.columns if c not in existing_columns]


def segmentation_enabled(config: dict) -> bool:
    """Whether to ask for the multi-axis segmentation alongside the summary."""
    return bool(config.get("segmentation", {}).get("enabled", True))


def build_summary_prompt(
    firm_name: str,
    search_results: list,
    config: dict,
    taxonomy: Optional[dict] = None,
) -> str:
    """Build the summary prompt based on configuration.

    When segmentation is enabled the taxonomy and its output contract are
    appended, so one model call produces both the prose summary and the
    structured classification instead of paying for two round trips per firm.
    """
    summary_config = config.get("summary", {})
    search_config = config.get("search", {})
    categories = config.get("categories", [])

    language = summary_config.get("language", "Korean")
    focus_areas = summary_config.get("focus_areas", [])
    custom_prompt = summary_config.get("custom_prompt", "")
    output_format = summary_config.get("output_format", "markdown")
    search_context = (search_config.get("context") or "").strip()

    # Build focus areas description
    focus_descriptions = {
        "business_areas": "business areas (what they do)",
        "research_technologies": "research areas and technologies",
        "job_openings": "job openings and career opportunities",
        "company_culture": "company culture and work environment",
        "products_services": "main products and services",
        "funding_investors": "funding and investors",
        "team_leadership": "team and leadership",
    }

    focus_text = ", ".join(
        focus_descriptions.get(area, area) for area in focus_areas
    )

    # Build categories description for classification
    category_descriptions = []
    for cat in categories:
        if cat.get("keywords"):
            keywords_str = ", ".join(cat["keywords"][:5])
            category_descriptions.append(
                f"- {cat['id']}: {cat['name']} ({cat.get('description', '')}). "
                f"Keywords: {keywords_str}"
            )
        else:
            category_descriptions.append(
                f"- {cat['id']}: {cat['name']} ({cat.get('description', '')})"
            )

    categories_text = "\n".join(category_descriptions)
    category_ids = [cat["id"] for cat in categories]

    segmentation_block = ""
    if taxonomy is not None:
        segmentation_block = seg.build_segmentation_section(taxonomy, language)

    # Use custom prompt if provided, otherwise build default
    if custom_prompt:
        prompt = render_template(
            custom_prompt,
            firm_name=firm_name,
            language=language,
            focus_areas=focus_text,
            categories=categories_text,
            category_ids=json.dumps(category_ids),
            search_results=json.dumps(search_results, ensure_ascii=False),
            output_format=output_format,
            search_context=search_context,
            segmentation_block=segmentation_block,
        )
        # A custom prompt written before segmentation existed has no
        # {segmentation_block} placeholder; append it rather than silently
        # dropping the classification the caller asked for.
        if segmentation_block and "segmentation" not in custom_prompt:
            prompt = f"{prompt}\n\n{segmentation_block}"
    else:
        segmentation_step = ""
        segmentation_field = ""
        if segmentation_block:
            segmentation_step = f"\n3. Segment the firm on every axis below.\n\n{segmentation_block}\n"
            # Plain string: interpolated verbatim into the f-string below, so
            # braces here must not be doubled.
            segmentation_field = ',\n  "segmentation": { ...위 구조... }'

        prompt = f"""
You are a helpful assistant. Analyze the search results for the firm '{firm_name}'.

1. Summarize the information in **{language}**.
   - Focus on: {focus_text}.
   - Format the summary in {output_format}.

2. Classify the firm into ONE of these categories:
{categories_text}
{segmentation_step}
Return your response in the following JSON format:
{{
  "summary": "Markdown string in {language}...",
  "category": "category_id from {category_ids}"{segmentation_field}
}}

Search Results:
{json.dumps(search_results, ensure_ascii=False)}

Additional search context from user:
{search_context or "N/A"}
"""

    return prompt


RATE_LIMIT_PATTERNS = (
    "rate limit",
    "reached the limit",
    "reach the limit",
    "limit exceeded",
    "quota",
    "quota exceeded",
)


def detect_rate_limit_message(message: str) -> bool:
    """Detect if message indicates rate limit."""
    lower_msg = message.lower()
    return any(pattern in lower_msg for pattern in RATE_LIMIT_PATTERNS)


def summarize_firm(
    firm_name: str,
    search_results: list,
    provider: LLMProvider,
    config: dict,
    taxonomy: Optional[dict] = None,
) -> Optional[dict]:
    """Summarize and segment one firm with the selected LLM provider."""
    summary_config = config.get("summary", {})
    system_prompt = summary_config.get("system_prompt") or DEFAULT_SYSTEM_PROMPT
    if taxonomy is not None:
        system_prompt = f"{system_prompt}\n\n{seg.SEGMENTATION_SYSTEM_PROMPT}"

    prompt = build_summary_prompt(firm_name, search_results, config, taxonomy)

    try:
        result_json = provider.complete_json(prompt, system=system_prompt)
    except LLMError as e:
        # Quota and rate-limit problems are worth stopping the whole run for:
        # continuing would burn through the remaining firms producing nothing.
        if detect_rate_limit_message(str(e)):
            raise QuotaExhausted(
                f"{provider.label} reported a rate limit or quota issue: {e}"
            ) from e
        print(f"Error summarizing {firm_name}: {e}")
        return None

    if not isinstance(result_json, dict):
        raise ValueError(f"Expected a JSON object for {firm_name}, got {type(result_json).__name__}.")

    summary_text = result_json.get("summary")
    if not summary_text:
        raise ValueError(f"LLM did not return a summary for {firm_name}.")

    if taxonomy is not None:
        result_json["segmentation"] = seg.validate_segmentation(
            result_json.get("segmentation"), taxonomy
        )

    return result_json


def get_category_info(category_id: str, config: dict) -> dict:
    """Get category information by ID."""
    categories = config.get("categories", [])
    for cat in categories:
        if cat["id"] == category_id:
            return cat
    # Default to general if not found
    return {"id": "general", "name": "General", "description": "Other industries"}


def main():
    parser = argparse.ArgumentParser(
        description="Search and summarize firm information with configurable categories"
    )
    parser.add_argument(
        "-i", "--input",
        default=str(FILTERED_CSV),
        help="Input CSV file with firms to process (default: the filter's output)"
    )
    parser.add_argument(
        "-o", "--output-dir",
        default=None,
        help="Output directory (overrides config)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without making API calls"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of firms to process"
    )
    parser.add_argument(
        "--provider",
        choices=PROVIDER_IDS,
        default=None,
        help="LLM provider to use (default: app.llm_provider in config.yml)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override the provider's model for this run",
    )
    parser.add_argument(
        "--no-segmentation",
        action="store_true",
        help="Skip the multi-axis taxonomy classification",
    )

    args = parser.parse_args()

    # Load configuration
    config = load_config()

    use_segmentation = segmentation_enabled(config) and not args.no_segmentation
    taxonomy = seg.load_taxonomy() if use_segmentation else None

    tavily_api_key = os.getenv("TAVILY_API_KEY")

    # Initialize clients
    if not args.dry_run:
        if not tavily_api_key:
            print("Error: TAVILY_API_KEY not found in environment variables.")
            sys.exit(1)

        tavily_client = TavilyClient(api_key=tavily_api_key)
        try:
            provider = get_provider(args.provider, config=config, model=args.model)
            # Fail here, before the first search, rather than after paying for one.
            provider.api_key()
        except LLMError as exc:
            print(f"Error: {exc}")
            sys.exit(1)
        print(f"Using {provider.label} ({provider.model})")
        if use_segmentation:
            print(f"Segmentation: on ({len(taxonomy['sectors'])} sectors)")
    else:
        tavily_client = None
        provider = None

    # Get output directory
    out_dir_conf = config.get("output", {}).get("directory", "firm_results")
    output_dir = Path(args.output_dir) if args.output_dir and os.path.isabs(args.output_dir) else (BASE_DIR / args.output_dir if args.output_dir else BASE_DIR / out_dir_conf)
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)

    # Check input file
    input_path = Path(args.input) if os.path.isabs(args.input) else BASE_DIR / "data" / args.input
    if not input_path.exists():
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"Error: {input_path} not found.")
            print("Run scripts/run_filter.py first to create the filtered CSV.")
            sys.exit(1)

    # Read CSV
    df = pd.read_csv(str(input_path))
    print(f"Loaded {len(df)} firms to process.")

    # Get search config
    search_config = config.get("search", {})
    query_template = search_config.get("query_template", "{firm_name} 채용 연구분야 사업내용")
    search_depth = search_config.get("search_depth", "advanced")
    max_results = search_config.get("max_results", 5)
    search_context = (search_config.get("context") or "").strip()

    # Track processed firms
    processed_folders = set()
    categories = config.get("categories", [])
    for cat in categories:
        category_path = output_dir / cat["id"]
        if category_path.is_dir():
            for entry in category_path.iterdir():
                processed_folders.add(entry.name)

    # Process firms
    firms_to_process = df
    if args.limit:
        firms_to_process = df.head(args.limit)

    valid_ids = {cat["id"] for cat in categories}
    write_csv = config.get("output", {}).get("create_csv_summary", True)
    csv_counts: dict = {}
    warned_csvs: set = set()
    processed_count = 0
    skipped_count = 0
    failures: list = []
    stopped_reason = None

    for row_number, (_, row) in enumerate(firms_to_process.iterrows(), start=1):
        raw_name = row.get("업체명")
        if pd.isna(raw_name) or not str(raw_name).strip():
            print(f"Skipping row {row_number}: no firm name.")
            continue
        firm_name = str(raw_name).strip()
        address = row.get("소재지", "")
        address = "" if pd.isna(address) else str(address)

        # Check if already processed
        safe_name = sanitize_filename(firm_name)
        if safe_name in ("", ".", ".."):
            failures.append((firm_name, "name is not usable as a folder name"))
            continue
        already_processed = False
        for cat in categories:
            cat_path = output_dir / cat["id"] / safe_name
            if safe_name in processed_folders or cat_path.exists():
                already_processed = True
                break

        if already_processed:
            print(f"Skipping [{row_number}/{len(firms_to_process)}] {firm_name} (already processed).")
            skipped_count += 1
            continue

        print(f"Processing [{row_number}/{len(firms_to_process)}] {firm_name}...")

        base_query = render_template(query_template, firm_name=firm_name)
        query = f"{base_query} {search_context}" if search_context else base_query

        if args.dry_run:
            print(f"  -> Would search: {query}")
            continue

        # Search
        try:
            search_response = tavily_client.search(
                query=query,
                search_depth=search_depth,
                max_results=max_results,
            )
        except Exception as e:
            print(f"Error searching for {firm_name}: {e}")
            failures.append((firm_name, f"search failed: {e}"))
            continue

        # Find firm webpage if enabled
        webpage_result = None
        if WEBPAGE_FINDER_AVAILABLE and search_config.get("find_webpage", True):
            try:
                webpage_result = find_firm_webpage(
                    firm_name,
                    tavily_client,
                    provider,
                    max_candidates=5
                )
            except Exception as e:
                print(f"  -> Warning: Could not find webpage: {e}")

        # Summarize, classify and segment. Only a spent quota stops the run;
        # any other failure is confined to this firm, which is left unwritten
        # so the next run retries it.
        try:
            result_data = summarize_firm(
                firm_name,
                search_response.get("results", []),
                provider,
                config,
                taxonomy,
            )
        except QuotaExhausted as err:
            stopped_reason = str(err)
            break
        except Exception as err:
            print(f"  -> Failed: {err}")
            failures.append((firm_name, str(err)))
            continue

        if result_data is None:
            failures.append((firm_name, "summarization failed"))
            continue

        summary = result_data.get("summary", "")
        segmentation = result_data.get("segmentation")

        # The coarse category decides the output directory. Prefer the one
        # implied by the segmented sector, so the two never disagree.
        if segmentation:
            category_id = seg.legacy_category(
                segmentation, taxonomy, {cat["id"] for cat in categories}
            )
        else:
            category_id = resolve_category_id(result_data.get("category"), valid_ids)
        category_info = get_category_info(category_id, config)

        # Create output directory for this firm
        firm_dir = output_dir / category_id / safe_name
        if not firm_dir.exists():
            firm_dir.mkdir(parents=True, exist_ok=True)

        processed_folders.add(safe_name)

        # Save raw search results
        with open(firm_dir / "raw_search.json", "w", encoding="utf-8") as f:
            json.dump(search_response, f, ensure_ascii=False, indent=2)

        # Save webpage information if found
        if webpage_result and webpage_result.get("url"):
            with open(firm_dir / "webpage.json", "w", encoding="utf-8") as f:
                json.dump(webpage_result, f, ensure_ascii=False, indent=2)

        # Save the segmentation on its own so downstream tools (Supabase sync,
        # notebooks) can read the structured record without parsing Markdown.
        if segmentation:
            with open(firm_dir / "segmentation.json", "w", encoding="utf-8") as f:
                json.dump(segmentation, f, ensure_ascii=False, indent=2)

        # Save summary
        with open(firm_dir / "summary.md", "w", encoding="utf-8") as f:
            f.write(f"# {firm_name}\n\n")
            f.write(f"**Address:** {address}\n")
            f.write(f"**Category:** {category_info['name']}\n")

            # Add webpage URL if found
            if webpage_result and webpage_result.get("url"):
                f.write(f"**Official Webpage:** [{webpage_result['url']}]({webpage_result['url']})\n")
                f.write(f"**Webpage Confidence:** {webpage_result.get('confidence', 'unknown')}\n")

            f.write("\n")
            if segmentation:
                f.write(seg.segmentation_markdown(segmentation, taxonomy))
                f.write("\n\n")
            f.write(summary)

        # Track for CSV summary
        firm_data = {
            "firm_name": firm_name,
            "address": address,
            "category": category_info["name"],
            "summary_snippet": summary[:100] + "..." if len(summary) > 100 else summary,
        }
        if segmentation:
            firm_data.update(seg.segmentation_columns(segmentation))

        # Add webpage URL if found
        if webpage_result and webpage_result.get("url"):
            firm_data["webpage"] = webpage_result["url"]
            firm_data["webpage_confidence"] = webpage_result.get("confidence", "unknown")
        else:
            firm_data["webpage"] = ""
            firm_data["webpage_confidence"] = ""
        
        if write_csv:
            csv_path = output_dir / f"{category_id}_firms.csv"
            missing = append_csv_row(csv_path, firm_data)
            if missing and csv_path not in warned_csvs:
                warned_csvs.add(csv_path)
                print(
                    f"  Note: {csv_path.name} predates columns {missing}; "
                    "they are dropped from its rows. Run firm-export for the "
                    "full schema, or delete the file to start it afresh."
                )
            csv_counts[csv_path] = csv_counts.get(csv_path, 0) + 1
        processed_count += 1

        if segmentation:
            verticals = ", ".join(segmentation.get("verticals") or []) or "-"
            print(
                f"  -> {segmentation['sector']}/{segmentation.get('subsector') or '-'}"
                f" | verticals: {verticals}"
                f" | model: {segmentation.get('business_model')}"
                f" | chain: {segmentation.get('value_chain')}"
                f" (confidence {segmentation['confidence'].get('sector')})"
            )
        else:
            print(f"  -> Classified as {category_info['name']}")
        time.sleep(1)  # Respect rate limits

    for csv_path, count in csv_counts.items():
        print(f"Wrote {count} firm(s) to {csv_path}")

    print(
        f"Summary: {processed_count} processed, {skipped_count} already done, "
        f"{len(failures)} failed."
    )
    if failures:
        print("Failed firms (re-run to retry them):")
        for name, reason in failures:
            print(f"  - {name}: {reason}")

    if stopped_reason:
        print(f"Stopping execution: {stopped_reason}")
        raise SystemExit(1)

    print("Done!")


if __name__ == "__main__":
    main()
