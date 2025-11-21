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
    base_url="https://models.inference.ai.azure.com",
    api_key=GITHUB_TOKEN,
)

INPUT_FILE = 'seoul_firms.csv'
OUTPUT_DIR = 'firm_results'

if not os.path.exists(INPUT_FILE):
    print(f"Error: {INPUT_FILE} not found. Run 1_filter_seoul.py first.")
    exit(1)

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

df = pd.read_csv(INPUT_FILE)
print(f"Loaded {len(df)} firms to process.")

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name)

def summarize_firm(firm_name, search_results):
    prompt = f"""
    You are a helpful assistant. Summarize the following search results for the firm '{firm_name}'.
    
    Focus on:
    1. What the company does (Business areas, products, services).
    2. Research areas and technologies they are involved in.
    3. Open job positions or recruitment information (if any).
    
    Format the output in Markdown.
    
    Search Results:
    {json.dumps(search_results, ensure_ascii=False)}
    """

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes company information."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error summarizing {firm_name}: {e}")
        return None

# Process firms
# For demonstration, let's process the first 5 firms. 
# Remove [:5] to process all.
firms_to_process = df.iloc[:5] 

for index, row in firms_to_process.iterrows():
    firm_name = row['업체명']
    address = row['소재지']
    
    safe_name = sanitize_filename(firm_name)
    firm_dir = os.path.join(OUTPUT_DIR, safe_name)
    
    if not os.path.exists(firm_dir):
        os.makedirs(firm_dir)
        
    # Check if already processed
    if os.path.exists(os.path.join(firm_dir, 'summary.md')):
        print(f"Skipping {firm_name} (already processed)")
        continue

    print(f"Processing [{index+1}/{len(df)}] {firm_name}...")

    # 1. Search
    try:
        query = f"{firm_name} 채용 연구분야 사업내용"
        search_response = tavily_client.search(query=query, search_depth="advanced", max_results=5)
        
        # Save raw search results
        with open(os.path.join(firm_dir, 'raw_search.json'), 'w', encoding='utf-8') as f:
            json.dump(search_response, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        print(f"Error searching for {firm_name}: {e}")
        continue

    # 2. Summarize
    summary = summarize_firm(firm_name, search_response.get('results', []))
    
    if summary:
        with open(os.path.join(firm_dir, 'summary.md'), 'w', encoding='utf-8') as f:
            f.write(f"# {firm_name}\n\n")
            f.write(f"**Address:** {address}\n\n")
            f.write(summary)
    
    time.sleep(1) # Respect rate limits

print("Done!")
