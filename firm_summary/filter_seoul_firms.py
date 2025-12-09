import pandas as pd
from tavily import TavilyClient
import time
import os

# Get the parent directory (project root)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

# Set your Tavily API key (get a free key at https://app.tavily.com/)
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "YOUR_TAVILY_API_KEY")
client = TavilyClient(api_key=TAVILY_API_KEY)

# Load CSV and filter for Seoul
input_file = os.path.join(DATA_DIR, "firms_sample.csv")
firms = pd.read_csv(input_file)
seoul_firms = firms[firms["주소"].str.contains("서울")]

results = []
for idx, row in seoul_firms.iterrows():
    query = f"{row['회사명']} 회사는 무엇을 하나요?"
    try:
        response = client.search(query=query, search_depth="basic")
        summary = response.get("answer", "정보 없음")
    except Exception as e:
        summary = f"API 오류: {e}"
    results.append({"회사명": row["회사명"], "주소": row["주소"], "설명": summary})
    time.sleep(1)  # avoid rate limits

result_df = pd.DataFrame(results)
output_file = os.path.join(DATA_DIR, "seoul_firms_with_info.csv")
result_df.to_csv(output_file, index=False, encoding="utf-8-sig")
print(result_df)
