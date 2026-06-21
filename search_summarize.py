#!/usr/bin/env python3
"""
Configurable Firm Search and Summarize Script

This script searches for firm information and generates summaries based on
user-defined configuration. Categories, prompts, and output format can all
be customized via config.json or command-line arguments.
"""

import argparse
import json
import os
import re
import sys
import time
import yaml
from typing import Optional

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
from tavily import TavilyClient

# Import firm webpage finder module with proper error handling
WEBPAGE_FINDER_AVAILABLE = False
find_firm_webpage = None

try:
    # Try to import from firm_summary package
    from firm_summary.find_firm_webpage import find_firm_webpage as _find_firm_webpage
    find_firm_webpage = _find_firm_webpage
    WEBPAGE_FINDER_AVAILABLE = True
except ImportError:
    # Fallback: Try direct import if module is in same directory or PYTHONPATH
    try:
        from find_firm_webpage import find_firm_webpage as _find_firm_webpage
        find_firm_webpage = _find_firm_webpage
        WEBPAGE_FINDER_AVAILABLE = True
    except ImportError:
        print("Warning: Firm webpage finder module not available")

# Load environment variables
load_dotenv()

DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful assistant that summarizes company information in JSON format."
)


def load_config(config_path: str = "config.yml") -> dict:
    """Load configuration from YAML or JSON file."""
    if os.path.exists(config_path) and config_path.endswith(('.yml', '.yaml')):
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
            
            # Load external summary config if specified
            summary_path = config.get("app", {}).get("summary_config_path")
            if summary_path and os.path.exists(summary_path):
                with open(summary_path, "r", encoding="utf-8") as sf:
                    summary_config = yaml.safe_load(sf) or {}
                    if "summary" in summary_config:
                        config["summary"] = summary_config["summary"]
                    if "categories" in summary_config:
                        config["categories"] = summary_config["categories"]
            return config
    elif os.path.exists(config_path) and config_path.endswith('.json'):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    elif os.path.exists("config.json"):
        with open("config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return get_default_config()


def get_default_config() -> dict:
    """Return default configuration."""
    return {
        "categories": [
            {
                "id": "finance",
                "name": "Finance/Quant",
                "description": "Finance, Financial Services, Quant Trading",
                "keywords": ["금융", "투자", "자산운용", "핀테크", "fintech", "quant"],
            },
            {
                "id": "general",
                "name": "General",
                "description": "Other industries",
                "keywords": [],
            },
        ],
        "summary": {
            "language": "Korean",
            "focus_areas": ["business_areas", "research_technologies", "job_openings"],
            "custom_prompt": "",
            "output_format": "markdown",
            "system_prompt": DEFAULT_SYSTEM_PROMPT,
        },
        "search": {
            "query_template": "{firm_name} 채용 연구분야 사업내용",
            "search_depth": "advanced",
            "max_results": 5,
            "context": "",
            "find_webpage": True,  # Enable firm webpage finding
        },
        "output": {
            "directory": "firm_results",
            "create_csv_summary": True,
        },
    }


def sanitize_filename(name: str) -> str:
    """Sanitize string for use as filename."""
    return re.sub(r'[\\/*?:"<>|]', "", name)


def build_summary_prompt(
    firm_name: str,
    search_results: list,
    config: dict,
) -> str:
    """Build the summary prompt based on configuration."""
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

    # Use custom prompt if provided, otherwise build default
    if custom_prompt:
        prompt = custom_prompt.format(
            firm_name=firm_name,
            language=language,
            focus_areas=focus_text,
            categories=categories_text,
            category_ids=json.dumps(category_ids),
            search_results=json.dumps(search_results, ensure_ascii=False),
            output_format=output_format,
            search_context=search_context,
        )
    else:
        prompt = f"""
You are a helpful assistant. Analyze the search results for the firm '{firm_name}'.

1. Summarize the information in **{language}**.
   - Focus on: {focus_text}.
   - Format the summary in {output_format}.

2. Classify the firm into ONE of these categories:
{categories_text}

Return your response in the following JSON format:
{{
  "summary": "Markdown string in {language}...",
  "category": "category_id from {category_ids}"
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
    openai_client: OpenAI,
    config: dict,
) -> Optional[dict]:
    """Summarize firm information using LLM."""
    summary_config = config.get("summary", {})
    system_prompt = summary_config.get("system_prompt") or DEFAULT_SYSTEM_PROMPT
    prompt = build_summary_prompt(firm_name, search_results, config)

    try:
        model_name = config.get("app", {}).get("model_selection", "gpt-4o")
        response = openai_client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            response_format={"type": "json_object"},
        )
    except Exception as e:
        print(f"Error summarizing {firm_name}: {e}")
        return None

    if not response.choices:
        raise ValueError(f"No response returned for {firm_name}.")

    message_content = response.choices[0].message.content or ""
    if not message_content.strip():
        raise ValueError(f"Empty response returned for {firm_name}.")

    if detect_rate_limit_message(message_content):
        raise RuntimeError(
            "LLM indicated a rate limit or quota issue. Please check your API usage."
        )

    result_json = json.loads(message_content)
    summary_text = result_json.get("summary")
    if not summary_text:
        raise ValueError(f"LLM did not return a summary for {firm_name}.")

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
        default="seoul_firms.csv",
        help="Input CSV file with firms to process"
    )
    parser.add_argument(
        "-c", "--config",
        default="config.yml",
        help="Configuration file path"
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

    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)

    # Get API keys
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    github_token = os.getenv("GITHUB_TOKEN")
    openai_base_url = os.getenv("OPENAI_BASE_URL", "https://models.github.ai/inference")

    if not args.dry_run:
        if not tavily_api_key:
            print("Error: TAVILY_API_KEY not found in environment variables.")
            sys.exit(1)
        if not github_token:
            print("Error: GITHUB_TOKEN not found in environment variables.")
            sys.exit(1)

    # Initialize clients
    if not args.dry_run:
        tavily_client = TavilyClient(api_key=tavily_api_key)
        openai_client = OpenAI(
            base_url=openai_base_url,
            api_key=github_token,
        )
    else:
        tavily_client = None
        openai_client = None

    # Get output directory
    output_dir = args.output_dir or config.get("output", {}).get("directory", "firm_results")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Check input file
    if not os.path.exists(args.input):
        print(f"Error: {args.input} not found.")
        print("Run filter_firms.py first to create the filtered CSV.")
        sys.exit(1)

    # Read CSV
    df = pd.read_csv(args.input)
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
        category_path = os.path.join(output_dir, cat["id"])
        if os.path.isdir(category_path):
            for entry in os.listdir(category_path):
                processed_folders.add(entry)

    # Process firms
    firms_to_process = df
    if args.limit:
        firms_to_process = df.head(args.limit)

    category_firms = {cat["id"]: [] for cat in categories}

    for row_number, (_, row) in enumerate(firms_to_process.iterrows(), start=1):
        firm_name = row["업체명"]
        address = row.get("소재지", "")

        # Check if already processed
        safe_name = sanitize_filename(firm_name)
        already_processed = False
        for cat in categories:
            cat_path = os.path.join(output_dir, cat["id"], safe_name)
            if safe_name in processed_folders or os.path.exists(cat_path):
                already_processed = True
                break

        if already_processed:
            print(f"Skipping {firm_name} (already processed).")
            continue

        print(f"Processing [{row_number}/{len(firms_to_process)}] {firm_name}...")

        base_query = query_template.format(firm_name=firm_name)
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
            continue

        # Find firm webpage if enabled
        webpage_result = None
        if WEBPAGE_FINDER_AVAILABLE and search_config.get("find_webpage", True):
            try:
                webpage_result = find_firm_webpage(
                    firm_name,
                    tavily_client,
                    openai_client,
                    max_candidates=5
                )
            except Exception as e:
                print(f"  -> Warning: Could not find webpage: {e}")

        # Summarize and classify
        try:
            result_data = summarize_firm(
                firm_name,
                search_response.get("results", []),
                openai_client,
                config,
            )
        except Exception as err:
            print(f"Stopping execution: {err}")
            raise SystemExit(1) from err

        if result_data is None:
            raise RuntimeError(f"Summarization failed for {firm_name}.")

        summary = result_data.get("summary", "")
        category_id = result_data.get("category", "general")
        category_info = get_category_info(category_id, config)

        # Create output directory for this firm
        firm_dir = os.path.join(output_dir, category_id, safe_name)
        if not os.path.exists(firm_dir):
            os.makedirs(firm_dir)

        processed_folders.add(safe_name)

        # Save raw search results
        with open(os.path.join(firm_dir, "raw_search.json"), "w", encoding="utf-8") as f:
            json.dump(search_response, f, ensure_ascii=False, indent=2)

        # Save webpage information if found
        if webpage_result and webpage_result.get("url"):
            with open(os.path.join(firm_dir, "webpage.json"), "w", encoding="utf-8") as f:
                json.dump(webpage_result, f, ensure_ascii=False, indent=2)

        # Save summary
        with open(os.path.join(firm_dir, "summary.md"), "w", encoding="utf-8") as f:
            f.write(f"# {firm_name}\n\n")
            f.write(f"**Address:** {address}\n")
            f.write(f"**Category:** {category_info['name']}\n")
            
            # Add webpage URL if found
            if webpage_result and webpage_result.get("url"):
                f.write(f"**Official Webpage:** [{webpage_result['url']}]({webpage_result['url']})\n")
                f.write(f"**Webpage Confidence:** {webpage_result.get('confidence', 'unknown')}\n")
            
            f.write("\n")
            f.write(summary)

        # Track for CSV summary
        firm_data = {
            "firm_name": firm_name,
            "address": address,
            "category": category_info["name"],
            "summary_snippet": summary[:100] + "..." if len(summary) > 100 else summary,
        }
        
        # Add webpage URL if found
        if webpage_result and webpage_result.get("url"):
            firm_data["webpage"] = webpage_result["url"]
            firm_data["webpage_confidence"] = webpage_result.get("confidence", "unknown")
        else:
            firm_data["webpage"] = ""
            firm_data["webpage_confidence"] = ""
        
        category_firms[category_id].append(firm_data)

        print(f"  -> Classified as {category_info['name']}")
        time.sleep(1)  # Respect rate limits

    # Save category CSV summaries
    if config.get("output", {}).get("create_csv_summary", True):
        for category_id, firms_list in category_firms.items():
            if firms_list:
                firms_df = pd.DataFrame(firms_list)
                csv_path = os.path.join(output_dir, f"{category_id}_firms.csv")

                if os.path.exists(csv_path):
                    firms_df.to_csv(
                        csv_path, mode="a", header=False, index=False, encoding="utf-8-sig"
                    )
                    print(f"Appended {len(firms_list)} firms to {csv_path}")
                else:
                    firms_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
                    print(f"Saved {len(firms_list)} firms to {csv_path}")

    print("Done!")


if __name__ == "__main__":
    main()
