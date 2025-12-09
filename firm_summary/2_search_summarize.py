import pandas as pd
import os
import json
import time
from tavily import TavilyClient
from openai import OpenAI
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not TAVILY_API_KEY:
    print("Error: TAVILY_API_KEY not found in environment variables.")
    exit(1)

if not GITHUB_TOKEN:
    print("Error: GITHUB_TOKEN not found in environment variables.")
    exit(1)

# Initialize clients
tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
openai_client = OpenAI(
    base_url="https://models.github.ai/inference",
    api_key=GITHUB_TOKEN,
)

# Get the parent directory (project root)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

INPUT_FILE = os.path.join(DATA_DIR, "seoul_firms.csv")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "firm_results")

if not os.path.exists(INPUT_FILE):
    print(f"Error: {INPUT_FILE} not found. Run 1_filter_seoul.py first.")
    exit(1)

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

df = pd.read_csv(INPUT_FILE)
print(f"Loaded {len(df)} firms to process.")

PROCESSED_FOLDERS = set()
for category in ("finance", "general"):
    category_path = os.path.join(OUTPUT_DIR, category)
    if os.path.isdir(category_path):
        for entry in os.listdir(category_path):
            PROCESSED_FOLDERS.add(entry)


def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name)


RATE_LIMIT_PATTERNS = (
    "rate limit",
    "reached the limit",
    "reach the limit",
    "limit exceeded",
    "quota",
    "quota exceeded",
)


def _detect_rate_limit_message(message: str) -> bool:
    lower_msg = message.lower()
    return any(pattern in lower_msg for pattern in RATE_LIMIT_PATTERNS)


def summarize_firm(firm_name, search_results):
    prompt = f"""
    You are a helpful assistant. Analyze the search results for the firm '{firm_name}'.

    1. Summarize the information in **Korean**.
       - Focus on business areas (what they do), research areas/technologies, and job openings.
       - Format the summary in Markdown.

    2. Classify if the firm is related to **Finance (Financial Services)** or **Quant (Quantitative Analysis/Trading)**.
       - Return 'true' if it is finance/quant related, 'false' otherwise.

    Return your response in the following JSON format:
    {{
      "summary": "Markdown string in Korean...",
      "is_finance_quant": true/false
    }}

    Search Results:
    {json.dumps(search_results, ensure_ascii=False)}
    """

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that summarizes company information in JSON format.",
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

    if _detect_rate_limit_message(message_content):
        raise RuntimeError(
            "LLM indicated a rate limit or quota issue. Please check your API usage."
        )

    result_json = json.loads(message_content)
    summary_text = result_json.get("summary")
    if not summary_text:
        raise ValueError(f"LLM did not return a summary for {firm_name}.")

    return result_json


# Process firms
# Process all firms
firms_to_process = df

finance_firms_list = []
errors_encountered = []

try:
    for row_number, (_, row) in enumerate(firms_to_process.iterrows(), start=1):
        firm_name = row["업체명"]
        address = row["소재지"]

        # Check if already processed
        safe_name = sanitize_filename(firm_name)
        finance_path = os.path.join(OUTPUT_DIR, "finance", safe_name)
        general_path = os.path.join(OUTPUT_DIR, "general", safe_name)

        if (
            safe_name in PROCESSED_FOLDERS
            or os.path.exists(finance_path)
            or os.path.exists(general_path)
        ):
            print(f"Skipping {firm_name} (already processed).")
            continue

        print(f"Processing [{row_number}/{len(df)}] {firm_name}...")

        # 1. Search
        try:
            query = f"{firm_name} 채용 연구분야 사업내용"
            search_response = tavily_client.search(
                query=query, search_depth="advanced", max_results=5
            )
        except Exception as e:
            error_msg = f"Search error for {firm_name}: {e}"
            print(f"ERROR: {error_msg}")
            errors_encountered.append(error_msg)
            continue

        # 2. Summarize and Classify
        try:
            result_data = summarize_firm(firm_name, search_response.get("results", []))
        except Exception as err:
            error_msg = f"Summarization error for {firm_name}: {err}"
            print(f"CRITICAL ERROR: {error_msg}")
            errors_encountered.append(error_msg)
            raise SystemExit(1) from err

        if result_data is None:
            error_msg = f"Summarization failed for {firm_name} (returned None)"
            print(f"ERROR: {error_msg}")
            errors_encountered.append(error_msg)
            raise RuntimeError(error_msg)

        summary = result_data.get("summary", "")
        is_finance = result_data.get("is_finance_quant", False)

        # Determine folder
        category_folder = "finance" if is_finance else "general"
        safe_name = sanitize_filename(firm_name)
        firm_dir = os.path.join(OUTPUT_DIR, category_folder, safe_name)

        if not os.path.exists(firm_dir):
            os.makedirs(firm_dir)

        PROCESSED_FOLDERS.add(safe_name)

        # Save raw search
        try:
            with open(
                os.path.join(firm_dir, "raw_search.json"), "w", encoding="utf-8"
            ) as f:
                json.dump(search_response, f, ensure_ascii=False, indent=2)
        except Exception as e:
            error_msg = f"Failed to save raw_search.json for {firm_name}: {e}"
            print(f"ERROR: {error_msg}")
            errors_encountered.append(error_msg)

        # Save summary
        try:
            with open(os.path.join(firm_dir, "summary.md"), "w", encoding="utf-8") as f:
                f.write(f"# {firm_name}\n\n")
                f.write(f"**Address:** {address}\n")
                f.write(
                    f"**Category:** {'Finance/Quant' if is_finance else 'General'}\n\n"
                )
                f.write(summary)
        except Exception as e:
            error_msg = f"Failed to save summary.md for {firm_name}: {e}"
            print(f"ERROR: {error_msg}")
            errors_encountered.append(error_msg)

        if is_finance:
            finance_firms_list.append(
                {
                    "firm_name": firm_name,
                    "address": address,
                    "summary_snippet": summary[:100] + "...",
                }
            )
            print(f"  -> Classified as Finance/Quant")
        else:
            print(f"  -> Classified as General")

        time.sleep(1)  # Respect rate limits

except KeyboardInterrupt:
    print("\n\nERROR: Script interrupted by user (Ctrl+C)")
    print(f"Processed {row_number}/{len(df)} firms before interruption")
    if errors_encountered:
        print(f"\nEncountered {len(errors_encountered)} error(s) before interruption:")
        for err in errors_encountered:
            print(f"  - {err}")
    raise SystemExit(130)  # Standard exit code for Ctrl+C

except Exception as e:
    print(f"\n\nCRITICAL ERROR: Unexpected error occurred: {e}")
    if errors_encountered:
        print(f"\nPrevious errors encountered:")
        for err in errors_encountered:
            print(f"  - {err}")
    raise SystemExit(1)

# Save finance firms CSV
try:
    if finance_firms_list:
        finance_df = pd.DataFrame(finance_firms_list)
        finance_csv_path = os.path.join(OUTPUT_DIR, "finance_firms.csv")

        if os.path.exists(finance_csv_path):
            finance_df.to_csv(
                finance_csv_path,
                mode="a",
                header=False,
                index=False,
                encoding="utf-8-sig",
            )
            print(
                f"Appended {len(finance_firms_list)} finance firms to {finance_csv_path}"
            )
        else:
            finance_df.to_csv(finance_csv_path, index=False, encoding="utf-8-sig")
            print(
                f"Saved {len(finance_firms_list)} finance firms to {finance_csv_path}"
            )
    else:
        print("No finance firms found in this batch.")
except Exception as e:
    print(f"ERROR: Failed to save finance_firms.csv: {e}")
    raise SystemExit(1)

# Final summary
print("\n" + "=" * 60)
if errors_encountered:
    print(f"COMPLETED WITH {len(errors_encountered)} ERROR(S)")
    print("=" * 60)
    print("\nErrors encountered:")
    for err in errors_encountered:
        print(f"  - {err}")
    print("\nNote: Non-critical errors were skipped, processing continued.")
else:
    print("COMPLETED SUCCESSFULLY")
    print("=" * 60)
print(f"Total firms processed: {len(df)}")
print(f"Finance/Quant firms found: {len(finance_firms_list)}")
