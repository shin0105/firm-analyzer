"""Upload processed firms to the Supabase `firms` table.

Joins the active 인원배정 list with the result folders and upserts one row per
firm. Summaries are uploaded with the AI notice (added if an older summary.md
lacks it). The raw search results are scraped web pages that can contain
personal data and third-party text, so they are only uploaded with
--include-raw-search, and only into a table that is not publicly readable.
"""

import argparse
import json
import os

import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client

from firm_analyzer.core.results import with_notice

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def clean_str(val):
    if val is None:
        return None
    return str(val).replace('\x00', '')

def read_summaries(include_raw_search: bool = False):
    from firm_analyzer.config import load_config, BASE_DIR
    config = load_config()
    out_dir_conf = config.get("output", {}).get("directory", "firm_results")
    results_dir = BASE_DIR / out_dir_conf
    summaries = {}
    
    if not results_dir.exists():
        return summaries
        
    for category in os.listdir(results_dir):
        cat_path = os.path.join(results_dir, category)
        if not os.path.isdir(cat_path):
            continue
            
        for firm_name in os.listdir(cat_path):
            firm_path = os.path.join(cat_path, firm_name)
            if not os.path.isdir(firm_path):
                continue
                
            firm_data = {
                'category': category,
                'summary_md': None,
                'raw_search': None,
                'webpage': None
            }
            
            # Read summary.md
            summary_path = os.path.join(firm_path, 'summary.md')
            if os.path.exists(summary_path):
                with open(summary_path, 'r', encoding='utf-8') as f:
                    firm_data['summary_md'] = clean_str(with_notice(f.read()))
                    
            # Read raw_search.json
            raw_search_path = os.path.join(firm_path, 'raw_search.json')
            if include_raw_search and os.path.exists(raw_search_path):
                with open(raw_search_path, 'r', encoding='utf-8') as f:
                    try:
                        content = f.read().replace('\x00', '')
                        firm_data['raw_search'] = json.loads(content)
                    except json.JSONDecodeError:
                        pass
                        
            # Read webpage.json
            webpage_path = os.path.join(firm_path, 'webpage.json')
            if os.path.exists(webpage_path):
                with open(webpage_path, 'r', encoding='utf-8') as f:
                    try:
                        content = f.read().replace('\x00', '')
                        firm_data['webpage'] = json.loads(content)
                    except json.JSONDecodeError:
                        pass
                        
            summaries[firm_name] = firm_data
            
    return summaries

def main():
    from firm_analyzer.core.roster import active_roster_path, normalize_roster, read_roster

    parser = argparse.ArgumentParser(description="Upload processed firms to Supabase")
    parser.add_argument(
        "--include-raw-search",
        action="store_true",
        help="Also upload raw_search.json (scraped pages; may contain personal data)",
    )
    args = parser.parse_args()

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Error: SUPABASE_URL and SUPABASE_KEY must be set in environment.")
        return

    print("Reading summaries...")
    summaries = read_summaries(include_raw_search=args.include_raw_search)

    csv_path = active_roster_path()
    if csv_path is None or not csv_path.exists():
        print("No 인원배정 list in data/. Import one with `firm-roster import <file>`.")
        return
    print(f"Reading {csv_path.name}...")
    df = normalize_roster(read_roster(csv_path))
    
    # Map CSV columns to DB columns
    records = []
    
    for idx, row in df.iterrows():
        name = str(row.get('업체명', '')).strip()
        if not name or name == 'nan':
            continue
            
        record = {
            'name': clean_str(name),
            'industry': clean_str(row.get('업종구분', '')),
            'location': clean_str(row.get('소재지', '')),
            # Column name kept for existing tables; it holds the active list's allocation.
            'allocation_2025': clean_str(row.get('배정인원', '')),
            'jurisdiction': clean_str(row.get('관할청', '')),
            'category': None,
            'summary_md': None,
            'raw_search': None,
            'webpage': None
        }
        
        # Merge with summary if exists
        if name in summaries:
            record.update(summaries[name])
            del summaries[name]
            
        records.append(record)
        
    # Add any remaining summaries that weren't in CSV
    for name, sum_data in summaries.items():
        record = {
            'name': clean_str(name),
            'industry': None,
            'location': None,
            'allocation_2025': None,
            'jurisdiction': None,
            'category': None,
            'summary_md': None,
            'raw_search': None,
            'webpage': None
        }
        record.update(sum_data)
        records.append(record)
        
    print(f"Total records parsed: {len(records)}")
    
    # Deduplicate by name
    unique_records = {}
    for r in records:
        unique_records[r['name']] = r
    records = list(unique_records.values())
    
    print(f"Total unique records to insert: {len(records)}")
    
    # Initialize Supabase Client
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    chunk_size = 100
    for i in range(0, len(records), chunk_size):
        chunk = records[i:i+chunk_size]
        print(f"Inserting {i} to {i+len(chunk)}...")
        
        # Remove \u0000 from the JSON string before sending
        chunk_cleaned = json.loads(json.dumps(chunk).replace('\\u0000', ''))
        
        try:
            # Use upsert to handle conflicts on 'name'
            response = supabase.table("firms").upsert(chunk_cleaned, on_conflict="name").execute()
        except Exception as e:
            print(f"Failed to insert chunk: {e}")
            
    print("Migration completed successfully!")

if __name__ == "__main__":
    main()
