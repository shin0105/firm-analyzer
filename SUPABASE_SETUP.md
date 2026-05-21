# Supabase Setup and Usage Guide

This document outlines how to set up, configure, and use Supabase for the Firm Analyzer project.

## 1. Initial Setup

### Project Creation
1. Go to [Supabase](https://supabase.com/) and sign in.
2. Click **New Project** and select your organization.
3. Provide a name (e.g., "Firm Analyzer"), a strong database password, and choose a region close to your users (e.g., Seoul).
4. Wait for the database to finish provisioning.

### Environment Variables
To connect your Flask application or Python scripts to Supabase, you need to set up your environment variables.
In the root of your project, create or update the `.env` file with the following variables:

```env
# Find these in Supabase Dashboard -> Settings -> API
SUPABASE_URL=your_project_url
SUPABASE_KEY=your_anon_api_key

# Find this in Supabase Dashboard -> Settings -> Database
SUPABASE_PW=your_database_password
```

## 2. Database Schema

The firm data is consolidated into a single PostgreSQL table named `firms`.

**Table: `firms`**
- `id`: Unique integer identifier (Primary Key)
- `name`: Name of the firm (Unique)
- `industry`: The industry category from the original CSV
- `location`: Address/Location of the firm
- `allocation_2025`: Number of allocated personnel for 2025
- `jurisdiction`: Regional jurisdiction
- `category`: AI-generated categorization (e.g., `ai_ml`, `finance`)
- `summary_md`: AI-generated summary in Markdown format
- `raw_search`: Raw JSON data from web search
- `webpage`: Raw JSON data from webpage scraping

## 3. Using Supabase in Python

To interact with Supabase in Python, you can either use the Supabase REST API (via the `requests` library) or the official `supabase` Python client.

### Option A: Using the REST API (Currently Used)
This method is lightweight and only requires the `requests` library.

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

### Option B: Using the Supabase Python Client
This method is more robust and pythonic. First, install the library:
`pip install supabase`

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

## 4. Managing Data (Dashboard)

You can manage your data without code using the Supabase Dashboard:

- **Table Editor**: Go to the Table Editor in the left sidebar to view, edit, add, or delete rows in the `firms` table manually, just like a spreadsheet.
- **SQL Editor**: Go to the SQL Editor to run complex queries, create views, or perform bulk updates.
- **CSV Export/Import**: You can export the current state of your table by clicking "Export data" in the Table Editor. You can also import new CSV data directly into the table from the dashboard.

## 5. Security (Row Level Security - RLS)

By default, the `firms` table has been configured with Row Level Security enabled, and a permissive policy has been applied to allow anonymous (`anon`) role access for all operations (Select, Insert, Update, Delete) to facilitate easy development. 

If you move this application to a public production environment where users shouldn't be able to edit the database, you should restrict these policies in the Supabase Dashboard under **Authentication -> Policies**.
