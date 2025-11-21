import pandas as pd
import os

# File paths
input_file = '2025_전문연구요원_인원배정.csv'
output_file = 'seoul_firms.csv'

# Check if input file exists
if not os.path.exists(input_file):
    print(f"Error: {input_file} not found.")
    exit(1)

# Read CSV
try:
    df = pd.read_csv(input_file)
    print(f"Loaded {len(df)} rows from {input_file}")
except Exception as e:
    print(f"Error reading CSV: {e}")
    exit(1)

# Filter for Seoul
# Column name for address is '소재지'
if '소재지' not in df.columns:
    print("Error: Column '소재지' not found in CSV.")
    print("Columns found:", df.columns)
    exit(1)

seoul_df = df[df['소재지'].str.contains('서울', na=False)]

# Save to new CSV
seoul_df.to_csv(output_file, index=False, encoding='utf-8-sig')
print(f"Filtered {len(seoul_df)} firms in Seoul.")
print(f"Saved to {output_file}")
