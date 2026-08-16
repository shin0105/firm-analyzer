import os
import json
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def clean_str(val):
    if val is None:
        return None
    return str(val).replace('\x00', '')

def read_summaries():
    from src.firm_analyzer.config import load_config, BASE_DIR
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
                    firm_data['summary_md'] = clean_str(f.read())
                    
            # Read raw_search.json
            raw_search_path = os.path.join(firm_path, 'raw_search.json')
            if os.path.exists(raw_search_path):
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
    from src.firm_analyzer.config import BASE_DIR

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Error: SUPABASE_URL and SUPABASE_KEY must be set in environment.")
        return

    print("Reading summaries...")
    summaries = read_summaries()
    
    print("Reading CSV...")
    csv_path = BASE_DIR / 'data/2025_전문연구요원_인원배정_parsed.csv'
    if not csv_path.exists():
        print(f"File not found: {csv_path}")
        return
    df = pd.read_csv(str(csv_path))
    
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
            'allocation_2025': clean_str(row.get('25년 배정인원', '')),
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
