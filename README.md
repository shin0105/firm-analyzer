# Firm Analyzer - 기업 분석 도구

A configurable web-based tool for filtering, searching, and summarizing firm/company information. Originally designed for Korean professional researcher personnel allocation (전문연구요원 인원배정) data, now extended to be flexible for any user-defined use case.

## Features

### 🔧 Configurable Filters
- **Location-based filtering**: Filter firms by any location/region, not just Seoul
- **Multiple filter types**: Contains, exact match, or starts-with patterns
- **Custom column selection**: Choose which CSV column to filter on

### 📁 Custom Categories
- **Define your own categories**: Not limited to Finance/Quant
- **Keyword-based classification**: AI automatically classifies firms based on your keywords
- **Color-coded**: Visual distinction between categories

### 📝 Customizable Summaries
- **Language selection**: Korean, English, Japanese, or Chinese
- **Focus areas**: Choose what information to include (business, research, jobs, culture, etc.)
- **Custom prompts**: Write your own LLM prompts for specific needs

### 🌐 Web Interface
- **Visual configuration**: No need to edit JSON files
- **Real-time results**: View processed firms by category
- **Run controls**: Execute filter and summarize scripts from the browser

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables

```bash
export TAVILY_API_KEY="your_tavily_api_key"
export GITHUB_TOKEN="your_github_token"  # For OpenAI via GitHub Models
```

Or create a `.env` file:
```
TAVILY_API_KEY=your_tavily_api_key
GITHUB_TOKEN=your_github_token
```

#### Optional Environment Variables

```bash
# Custom OpenAI-compatible endpoint (default: GitHub Models)
export OPENAI_BASE_URL="https://api.openai.com/v1"

# Enable Flask debug mode (default: false, for development only)
export FLASK_DEBUG="true"

# Script timeout settings (in seconds)
export FILTER_SCRIPT_TIMEOUT="60"
export SUMMARIZE_SCRIPT_TIMEOUT="300"
export DRY_RUN_TIMEOUT="60"
```

### 3. Run the Web Interface

```bash
python app.py
```

Open http://localhost:5000 in your browser.

## Command Line Usage

### Filter Firms

```bash
# Use config.json settings
python filter_firms.py

# Override with command line
python filter_firms.py --locations 서울 경기 --filter-type contains

# Different input file
python filter_firms.py -i my_firms.csv -o filtered.csv
```

### Search and Summarize

```bash
# Dry run (no API calls)
python search_summarize.py --dry-run

# Process limited number of firms
python search_summarize.py --limit 10

# Use custom config
python search_summarize.py --config my_config.json
```

## Configuration

All settings are stored in `config.json`. You can edit this file directly or use the web interface.

### Example Configuration

```json
{
  "filters": {
    "location": {
      "enabled": true,
      "type": "contains",
      "values": ["서울", "경기"],
      "column": "소재지"
    }
  },
  "categories": [
    {
      "id": "finance",
      "name": "Finance/Quant",
      "keywords": ["금융", "투자", "핀테크"],
      "color": "#4CAF50"
    },
    {
      "id": "ai_ml",
      "name": "AI/ML",
      "keywords": ["인공지능", "머신러닝", "딥러닝"],
      "color": "#9C27B0"
    },
    {
      "id": "general",
      "name": "General",
      "keywords": [],
      "color": "#607D8B"
    }
  ],
  "summary": {
    "language": "Korean",
    "focus_areas": ["business_areas", "research_technologies", "job_openings"],
    "custom_prompt": ""
  },
  "search": {
    "query_template": "{firm_name} 채용 연구분야 사업내용",
    "search_depth": "advanced",
    "max_results": 5
  }
}
```

## File Structure

```
firm_websearch/
├── app.py                  # Flask web application
├── filter_firms.py         # Configurable filter script
├── search_summarize.py     # Configurable search & summarize script
├── config.json             # Configuration file
├── templates/
│   └── index.html          # Web interface template
├── firm_results/           # Output directory
│   ├── finance/            # Firms classified as finance
│   ├── ai_ml/              # Firms classified as AI/ML
│   └── general/            # General category firms
├── 1_filter_seoul.py       # Legacy: Seoul-only filter
├── 2_search_summarize.py   # Legacy: Fixed categories
└── README.md
```

## Legacy Scripts

The original scripts (`1_filter_seoul.py` and `2_search_summarize.py`) are preserved for backwards compatibility. The new scripts (`filter_firms.py`, `search_summarize.py`, `app.py`) provide enhanced configurability.

## API Endpoints (Web Interface)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main web interface |
| `/api/config` | GET | Get current configuration |
| `/api/config` | POST | Update configuration |
| `/api/config/reset` | POST | Reset to default configuration |
| `/api/results/summary` | GET | Get summary of processed results |
| `/api/results/<category_id>` | GET | Get firms in a category |
| `/api/run/filter` | POST | Run filter script |
| `/api/run/summarize` | POST | Run search/summarize script |

## Use Cases

### 1. Research Institution Analysis
Filter by specific regions and categorize by research focus areas.

### 2. Job Market Research
Focus summaries on job openings and team information.

### 3. Investment Research
Create categories for different investment sectors and analyze company financials.

### 4. Regional Business Analysis
Filter by multiple regions and compare distributions.

## License

MIT License
