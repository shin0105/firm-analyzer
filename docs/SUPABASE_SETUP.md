# Supabase Setup and Usage Guide

This document outlines how to set up, configure, and use Supabase for the Firm Analyzer project.

## 1. Initial Setup

### Project Creation
1. Go to [Supabase](https://supabase.com/) and sign in.
2. Click **New Project** and select your organization.
3. Provide a name (e.g., "Firm Analyzer"), a strong database password, and choose a region close to your users (e.g., Seoul).
4. Wait for the database to finish provisioning.

### Environment Variables
To connect the upload command (`firm-supabase-sync`) or the web app (`firm-app`) to Supabase, set two variables.
In the root of your project, create or update the `.env` file with the following variables:

```env
# Find these in Supabase Dashboard -> Settings -> API
SUPABASE_URL=your_project_url
SUPABASE_KEY=your_anon_api_key
```

Both commands read the same two variables; there is no separate key for writing. Both load `.env` themselves, and a variable already set in the shell takes precedence over `.env`. The database password from project creation is not used by this project (`.env.example` lists `SUPABASE_PW`, but no code reads it).

## 2. Database Schema

The firm data is consolidated into a single PostgreSQL table named `firms`.

**Table: `firms`**
- `id`: Unique integer identifier (Primary Key). The sync never sends it.
- `name`: Name of the firm (Unique). The sync upserts on this column, so it needs a unique constraint.
- `industry`: `업종구분` from the active 인원배정 list
- `location`: `소재지` (address) from the active list
- `allocation_2025` (text): The active list's `배정인원` value, as text (e.g. `2`, `총괄배정`). The column name is kept for existing tables; it holds whichever year's list is active.
- `jurisdiction`: `관할청` (regional jurisdiction) from the active list
- `category`: The category folder the firm's results are in, i.e. a category id from `config.yml` (e.g., `ai_ml`, `finance`). Empty for firms not summarized yet.
- `summary_md`: AI-generated summary in Markdown format. `firm-supabase-sync` adds the AI-generated notice to any summary that lacks it, so the label travels with the text.
- `raw_search` (jsonb): Raw JSON data from web search. Empty unless you run `firm-supabase-sync --include-raw-search`: it holds the text of scraped pages, which can include personal data and third-party copyrighted material.
- `webpage` (jsonb): The firm's `webpage.json` from the webpage finder: `{"url", "confidence", "reasoning"}`. Empty when no official site was found.

There are no segmentation columns: `segmentation.json` is not uploaded (the `## 세분류` table is part of `summary_md`).

## 3. Uploading Results

```bash
uv run firm-supabase-sync

# Also upload raw_search.json, only into a table that is not publicly readable
uv run firm-supabase-sync --include-raw-search
```

The command reads the active 인원배정 list (`uv run firm-roster list` marks it with `*`), adds each firm's `summary.md` and `webpage.json` from `firm_results/<category>/<firm>/`, and upserts one row per firm name in batches of 100. Result folders whose firm is not in the active list are uploaded too, with only `name`, `category` and the result files.

A batch that fails prints `Failed to insert chunk: ...` and the run continues; the closing "completed" message is printed either way, so check the output.

## 4. Using Supabase in Python

To interact with Supabase in Python, you can use the official `supabase` Python client, as this project does, or the Supabase REST API directly.

### Option A: Using the Supabase Python Client (Used by this project)
`firm-supabase-sync` and the web app use this client. It is installed with the project's dependencies (`uv sync`).

```python
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# Fetching Data
response = supabase.table("firms").select("*").limit(5).execute()
print(response.data)

# Inserting Data
new_firm = {"name": "New Tech Co", "industry": "IT"}
supabase.table("firms").insert(new_firm).execute()
```

### Option B: Using the REST API
This method only requires the `requests` library.

```python
import os
import requests
from dotenv import load_dotenv

load_dotenv()

url = f"{os.getenv('SUPABASE_URL')}/rest/v1/firms"
headers = {
    "apikey": os.getenv("SUPABASE_KEY"),
    "Authorization": f"Bearer {os.getenv('SUPABASE_KEY')}",
    "Content-Type": "application/json"
}

# Fetching Data
response = requests.get(url, headers=headers)
data = response.json()
print(data)
```

## 5. Reading Supabase from the Web App

By default (`app.data_source: csv` in `config.yml`) the web app reads only the local `firm_results/` folders. With `app.data_source: supabase`, and `SUPABASE_URL` and `SUPABASE_KEY` set when `firm-app` starts:

- the dashboard counts (`/api/results/summary`) and the per-category lists (`/api/results/<category>`) come from the `firms` table, falling back to the local folders if the query fails;
- firm search and firm detail (`/api/firms`, `/api/firms/<category>/<firm>`) still read the local folders, because the segmentation they filter on is only stored there.

## 6. Managing Data (Dashboard)

You can manage your data without code using the Supabase Dashboard:

- **Table Editor**: Go to the Table Editor in the left sidebar to view, edit, add, or delete rows in the `firms` table manually, just like a spreadsheet.
- **SQL Editor**: Go to the SQL Editor to run complex queries, create views, or perform bulk updates.
- **CSV Export/Import**: You can export the current state of your table by clicking "Export data" in the Table Editor. You can also import new CSV data directly into the table from the dashboard.

## 7. Security (Row Level Security - RLS)

The `SUPABASE_KEY` this project uses is the anon (publishable) key, which is public by design: anyone who has it can do whatever the table's policies allow. Row Level Security policies are therefore the only thing protecting the data.

A permissive development policy (anon may select, insert, update and delete) lets anyone with the key rewrite or wipe the table. Before exposing the table or the app publicly:

- Allow the `anon` role `SELECT` only, and run `firm-supabase-sync` with a key that has write access, from a trusted machine. Since the sync and the app share `SUPABASE_KEY`, keep the anon key in `.env` and set the write key in the shell only for the sync run (a shell variable overrides `.env`).
- Do not upload `raw_search` to a publicly readable table.
- Keep the AI-generated notice on summaries you show to others (see [DISCLAIMER.md](../DISCLAIMER.md)).

Policies live in the Supabase Dashboard under **Authentication -> Policies**.
