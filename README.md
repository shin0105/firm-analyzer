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

### 🔎 Search Controls
- **Persistent context**: Append reusable Tavily search context to every query for better recall
- **Depth & limits**: Choose search depth and max result count

### 📝 Customizable Summaries
- **Language selection**: Korean, English, Japanese, or Chinese
- **Focus areas**: Choose what information to include (business, research, jobs, culture, etc.)
- **Custom prompts**: Write your own LLM prompts for specific needs
- **System prompt control**: Tune the assistant role/persona used for summary generation

### 🌐 Web Interface
- **Visual configuration**: No need to edit JSON files
- **Real-time results**: View processed firms by category
- **Run controls**: Execute filter and summarize scripts from the browser

### 📄 PDF to CSV Parser (New!)
- **Flexible column mapping**: Parse any PDF table format with custom column names
- **Automatic city extraction**: Extract city names from Korean addresses
- **Smart header detection**: Automatically identifies table headers in PDFs
- **Column renaming**: Map source columns to target column names
- **Multiple format support**: Works with various Korean company list PDFs

## Quick Start

### Option A: Using UV (Recommended)

[UV](https://docs.astral.sh/uv/) is a fast Python package manager that replaces pip, conda, and other tools. It's much faster and provides better dependency resolution.

#### 1. Install UV

```bash
# On macOS and Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or via pip
pip install uv

# Or via Homebrew
brew install uv
```

#### 2. Install Dependencies

```bash
# This will automatically create a virtual environment and install all dependencies
uv sync
```

#### 3. Set Environment Variables

Create a `.env` file:
```
TAVILY_API_KEY=your_tavily_api_key
GITHUB_TOKEN=your_github_token
```

#### 4. Run the Web Interface

```bash
# Run any Python script using uv run
uv run python app.py
```

Open http://localhost:8001 in your browser.

#### 5. Run Command Line Scripts

```bash
# Filter firms
uv run python filter_firms.py

# Search and summarize with options
uv run python search_summarize.py --dry-run
uv run python search_summarize.py --limit 10
```

### Option B: Using pip (Traditional)

#### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 2. Set Environment Variables

Create a `.env` file (same as UV option above):
```
TAVILY_API_KEY=your_tavily_api_key
GITHUB_TOKEN=your_github_token
```

#### 3. Run the Web Interface

```bash
python app.py
```

Open http://localhost:8001 in your browser.

Available pages:
- 🔧 **Configuration/Summary**: `http://localhost:8001/`
- 🚇 **Map-based Firm Viewer**: `http://localhost:8001/firms` (with subway lines)

#### 4. Run Command Line Scripts

```bash
# Filter firms
python filter_firms.py

# Search and summarize with options
python search_summarize.py --dry-run
python search_summarize.py --limit 10
```

### Optional Environment Variables

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

## Command Line Usage

All examples below work with both UV and pip installations. Simply prefix commands with `uv run` when using UV.

### Filter Firms

```bash
# With UV
uv run python filter_firms.py

# With pip (traditional)
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

### Parse PDF to CSV (New!)

```bash
# Parse PDF with default settings
python firm_summary/parse_pdf_to_csv_extended.py

# Extract city from location and add as a column
python firm_summary/parse_pdf_to_csv_extended.py --extract-city-from-location

# Parse custom PDF with column mapping
python firm_summary/parse_pdf_to_csv_extended.py \
  --pdf data/korean_companies.pdf \
  --output data/korean_companies.csv \
  --columns "번호" "회사명" "상세주소" "도시"

# Rename columns while parsing
python firm_summary/parse_pdf_to_csv_extended.py \
  --columns "번호:Number" "회사명:Company Name" "소재지:Location" \
  --extract-city-from-location

# For detailed documentation
See firm_summary/README_PDF_PARSER.md
```

## UV Package Management Guide

UV is a modern Python package manager that provides significant advantages over traditional tools like pip and conda.

### Why UV?

- **⚡ Lightning Fast**: 10-100x faster than pip for installing packages
- **🔒 Reliable**: Consistent dependency resolution with lockfiles
- **🎯 All-in-One**: Replaces pip, pip-tools, virtualenv, and more
- **💾 Efficient**: Global caching reduces disk space usage
- **🐍 Python Version Management**: Can install and manage Python versions

### Common UV Commands

```bash
# Install dependencies (creates virtual environment automatically)
uv sync

# Add a new dependency
uv add flask pandas

# Add a development dependency
uv add --dev pytest black

# Remove a dependency
uv remove package-name

# Update dependencies
uv lock --upgrade

# Run a Python script
uv run python script.py

# Run a command in the virtual environment
uv run flask run

# Install a specific Python version (if needed)
uv python install 3.12

# Create a new project
uv init

# Show installed packages
uv pip list
```

### UV vs Conda

If you previously used conda, here's the mapping:

| Conda Command | UV Equivalent |
|--------------|---------------|
| `conda create -n env` | `uv venv` (automatic with `uv sync`) |
| `conda activate env` | Automatic when using `uv run` |
| `conda install package` | `uv add package` |
| `conda remove package` | `uv remove package` |
| `conda list` | `uv pip list` |
| `conda env export` | `pyproject.toml` + `uv.lock` (together define environment) |

### Benefits Over Conda

1. **Speed**: UV is significantly faster for package installation
2. **Standard Python**: Uses PyPI packages directly, no special conda packages needed
3. **Smaller Footprint**: No need for large conda distribution
4. **Better for CI/CD**: Faster builds and deploys
5. **Lockfiles**: `uv.lock` ensures reproducible installations

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
    "custom_prompt": "",
    "system_prompt": "You are a helpful assistant that summarizes company information in JSON format."
  },
  "search": {
    "query_template": "{firm_name} 채용 연구분야 사업내용",
    "search_depth": "advanced",
    "max_results": 5,
    "context": "채용, 연구 분야, 주요 기술 스택을 중심으로 검색"
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
# Firm WebSearch

A web application for viewing and searching 2025 전문연구요원 인원배정 업체 현황 (Research Personnel Assignment Companies).

## Project Structure

```
firm_websearch/
├── data/                          # Data files (CSV)
│   ├── 2025_전문연구요원_인원배정.csv
│   └── seoul_firms.csv
├── firm_summary/                  # Firm data processing scripts
│   ├── 1_filter_seoul.py          # Filter Seoul-based firms
│   ├── 2_search_summarize.py      # Search and summarize firm info
│   ├── filter_seoul_firms.py      # Alternative filtering script
│   ├── generate_firms_data.py     # Generate JS data for webapp
│   └── test_url.py                # URL testing utility
├── firm_results/                  # Results from firm summarization
│   ├── finance/                   # Finance/Quant related firms
│   └── general/                   # General firms
├── webapp/                        # Flask web application
│   ├── app.py                     # Flask application entry point
│   ├── static/
│   │   ├── css/                   # Stylesheets
│   │   │   ├── firm_viewer.css
│   │   │   └── firms_viewer.css
│   │   └── js/                    # JavaScript files
│   │       ├── firm_viewer.js
│   │       ├── firms_viewer.js
│   │       └── firms_data.js
│   └── templates/                 # Jinja2 templates
│       ├── firm_viewer.html
│       └── firms_viewer.html
├── requirements.txt               # Python dependencies
└── README.md                      # This file
```

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/shin0105/firm_websearch.git
   cd firm_websearch
   ```

2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate     # Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Running the Web Application

Start the Flask development server:

```bash
cd webapp
python app.py
```

For development with debug mode enabled:

```bash
cd webapp
FLASK_DEBUG=1 python app.py
```

Then open your browser to:
- `http://localhost:5000/` - Main firms viewer
- `http://localhost:5000/firm-viewer` - Alternative firm viewer

### Running Firm Summary Scripts

1. **Filter Seoul firms:**
   ```bash
   cd firm_summary
   python 1_filter_seoul.py
   ```

2. **Search and summarize firms:**
   ```bash
   python 2_search_summarize.py
   ```

3. **Generate JS data for webapp:**
   ```bash
   python generate_firms_data.py
   ```

## Environment Variables

Create a `.env` file with the following variables for the summary scripts:

```
TAVILY_API_KEY=your_tavily_api_key
GITHUB_TOKEN=your_github_token
```

## Features

- Interactive map showing firm locations across Korea
- Region-based filtering (Seoul, Busan, etc.)
- Seoul district (구) filtering
- Search functionality
- Responsive design for mobile and desktop

## License

MIT License
