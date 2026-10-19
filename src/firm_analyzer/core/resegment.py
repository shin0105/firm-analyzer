#!/usr/bin/env python3
"""
Segment firms that were already summarized, from their saved search results.

summarize only segments firms it processes, and it skips every firm that
already has a result folder, so firms summarized before taxonomy.yml existed
(or before it last changed) never get a segmentation. This backfills them by
re-running only the classification step over each folder's raw_search.json:
no new Tavily searches, and one model call per firm.

For each selected firm it writes segmentation.json and places the 세분류
table in summary.md. With --relocate it also moves the folder to the category
its sector maps to, so the dashboard's coarse buckets reflect the new
classification.
"""

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

from firm_analyzer.config import load_config, results_dir
from firm_analyzer.core import segmentation as seg
from firm_analyzer.core.results import (
    SEGMENTATION_HEADING,
    insert_segmentation_block,
    iter_firm_dirs,
    load_json,
    parse_summary_header,
    read_text,
    set_header_field,
)
from firm_analyzer.core.summarize import detect_rate_limit_message
from firm_analyzer.llm import LLMError, PROVIDER_IDS, get_provider

load_dotenv()


def select_firms(output_dir: Path, category_ids: list, force: bool) -> tuple[list, int, int]:
    """Firm folders to segment, plus counts of those already done and unusable."""
    selected, already, no_search = [], 0, 0
    for category_id, firm_dir in iter_firm_dirs(output_dir, category_ids):
        if not (firm_dir / "raw_search.json").exists():
            no_search += 1
            continue
        if (firm_dir / "segmentation.json").exists() and not force:
            already += 1
            continue
        selected.append((category_id, firm_dir))
    return selected, already, no_search


def update_summary(summary_path: Path, segmentation: dict, previous: dict, taxonomy: dict) -> bool:
    """Put the new 세분류 block into summary.md. False if it could not be placed."""
    text = read_text(summary_path)
    if not text:
        return True  # no summary.md to update

    block = seg.segmentation_markdown(segmentation, taxonomy)
    if SEGMENTATION_HEADING in text:
        # Replace only a block we can reproduce exactly; anything else may have
        # been hand-edited, and guessing its extent risks eating the summary.
        old_block = seg.segmentation_markdown(previous, taxonomy) if previous else None
        if not old_block or old_block not in text:
            return False
        text = text.replace(old_block, block, 1)
    else:
        text = insert_segmentation_block(text, block)

    summary_path.write_text(text, encoding="utf-8")
    return True


def segment_firm(firm_dir: Path, provider, taxonomy: dict, config: dict) -> dict:
    """Classify one firm folder from its saved search results."""
    search = load_json(firm_dir / "raw_search.json")
    results = search.get("results", []) if isinstance(search, dict) else []
    if not results:
        raise ValueError("raw_search.json has no results to classify from")

    header = parse_summary_header(read_text(firm_dir / "summary.md"))
    prompt = seg.build_segmentation_prompt(
        header.name or firm_dir.name,
        results,
        taxonomy,
        language=config.get("summary", {}).get("language", "Korean"),
        webpage=load_json(firm_dir / "webpage.json"),
        extra_context=(config.get("search", {}).get("context") or "").strip(),
    )
    raw = provider.complete_json(prompt, system=seg.SEGMENTATION_SYSTEM_PROMPT)
    return seg.validate_segmentation(raw, taxonomy)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Segment already-summarized firms against taxonomy.yml, reusing their "
            "saved search results instead of searching again"
        )
    )
    parser.add_argument("-o", "--output-dir", default=None,
                        help="Results directory (default: output.directory in config.yml)")
    parser.add_argument("--category", action="append", default=None, metavar="ID",
                        help="Only firms in this category (repeatable)")
    parser.add_argument("--limit", type=int, default=None,
                        help="Segment at most this many firms")
    parser.add_argument("--force", action="store_true",
                        help="Re-segment firms that already have segmentation.json")
    parser.add_argument("--relocate", action="store_true",
                        help="Move each firm to the category its sector maps to")
    parser.add_argument("--dry-run", action="store_true",
                        help="List what would be segmented without calling a model")
    parser.add_argument("--provider", choices=PROVIDER_IDS, default=None,
                        help="LLM provider to use (default: app.llm_provider in config.yml)")
    parser.add_argument("--model", default=None,
                        help="Override the provider's model for this run")
    parser.add_argument("--delay", type=float, default=1.0,
                        help="Seconds to wait between model calls (default: 1)")
    args = parser.parse_args()

    config = load_config()
    taxonomy = seg.load_taxonomy()
    categories = config.get("categories", [])
    names = {cat["id"]: cat.get("name", cat["id"]) for cat in categories if cat.get("id")}

    category_ids = list(names)
    if args.category:
        unknown = [c for c in args.category if c not in names]
        if unknown:
            print(f"Error: unknown category {unknown}. Configured: {category_ids}")
            sys.exit(1)
        category_ids = args.category

    # Relative paths resolve against the project root, as in summarize.
    output_dir = results_dir({"output": {"directory": args.output_dir}} if args.output_dir else config)
    selected, already, no_search = select_firms(output_dir, category_ids, args.force)
    if args.limit:
        selected = selected[: args.limit]

    print(f"Results: {output_dir}")
    print(
        f"{len(selected)} firm(s) to segment; {already} already segmented, "
        f"{no_search} without saved search results."
    )

    if args.dry_run:
        for category_id, firm_dir in selected[:20]:
            print(f"  - {category_id}/{firm_dir.name}")
        if len(selected) > 20:
            print(f"  ... and {len(selected) - 20} more")
        return

    if not selected:
        print("Nothing to do.")
        return

    try:
        provider = get_provider(args.provider, config=config, model=args.model)
        provider.api_key()
    except LLMError as exc:
        print(f"Error: {exc}")
        sys.exit(1)
    print(f"Using {provider.label} ({provider.model})")

    valid_ids = set(names)
    segmented = 0
    moves: dict = {}
    failures: list = []
    summary_skipped: list = []
    stopped_reason = None

    for index, (category_id, firm_dir) in enumerate(selected, start=1):
        print(f"[{index}/{len(selected)}] {category_id}/{firm_dir.name}")
        previous = load_json(firm_dir / "segmentation.json")
        try:
            segmentation = segment_firm(firm_dir, provider, taxonomy, config)
        except LLMError as exc:
            if detect_rate_limit_message(str(exc)):
                stopped_reason = f"{provider.label} reported a rate limit or quota issue: {exc}"
                break
            print(f"  -> Failed: {exc}")
            failures.append((firm_dir.name, str(exc)))
            continue
        except Exception as exc:
            print(f"  -> Failed: {exc}")
            failures.append((firm_dir.name, str(exc)))
            continue

        with open(firm_dir / "segmentation.json", "w", encoding="utf-8") as handle:
            json.dump(segmentation, handle, ensure_ascii=False, indent=2)

        summary_path = firm_dir / "summary.md"
        if not update_summary(summary_path, segmentation,
                              previous if isinstance(previous, dict) else None, taxonomy):
            summary_skipped.append(firm_dir.name)

        segmented += 1
        target_id = seg.legacy_category(segmentation, taxonomy, valid_ids)
        print(
            f"  -> {segmentation['sector']}/{segmentation.get('subsector') or '-'}"
            f" (confidence {segmentation['confidence'].get('sector')})"
            f" -> category {target_id}"
        )

        if args.relocate and target_id != category_id:
            target_dir = output_dir / target_id / firm_dir.name
            if target_dir.exists():
                print(f"  -> Not moved: {target_dir} already exists")
            else:
                if summary_path.exists():
                    summary_path.write_text(
                        set_header_field(read_text(summary_path), "Category", names[target_id]),
                        encoding="utf-8",
                    )
                target_dir.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(firm_dir), str(target_dir))
                moves[(category_id, target_id)] = moves.get((category_id, target_id), 0) + 1

        time.sleep(args.delay)

    print(f"Summary: {segmented} segmented, {len(failures)} failed.")
    for (source, target), count in sorted(moves.items()):
        print(f"  moved {count} firm(s) {source} -> {target}")
    if summary_skipped:
        print(
            f"  {len(summary_skipped)} summary.md file(s) kept their existing 세분류 "
            "block (it did not match the previous segmentation.json exactly); "
            "segmentation.json is up to date."
        )
    if failures:
        print("Failed firms (re-run to retry them):")
        for name, reason in failures:
            print(f"  - {name}: {reason}")
    if segmented:
        print("Category CSVs are not rewritten; run firm-export for a CSV with every firm.")

    if stopped_reason:
        print(f"Stopping execution: {stopped_reason}")
        sys.exit(1)


if __name__ == "__main__":
    main()
