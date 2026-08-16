# Firm Analyzer - 기업 분석 도구

A configurable web-based tool for filtering, searching, and summarizing firm/company information. Originally designed for Korean professional researcher personnel allocation (전문연구요원 인원배정) data, now extended to be flexible for any user-defined use case.

📖 **New!** See [FIRM_DATA_FORMAT.md](docs/FIRM_DATA_FORMAT.md) for a comprehensive guide on CSV data format requirements and sample files in `data/samples/` directory.

## Features

### 🎯 Dual-Page Workflow Interface
- **Configuration Editor**: Dedicated page for editing all settings (filters, search, summaries, categories)
- **Results Viewer**: Separate page for browsing and searching processed firm summaries
- **Clean Navigation**: Easy switching between config, results, and map views

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
### 🗺️ Accurate Korean Map Display
- **Kakao Maps API integration**: Precise geocoding for Korean addresses
- **Dual address format support**: Works with both 도로명주소 (road name) and 지번주소 (lot number) addresses
- **Interactive map viewer**: View firms on an accurate map with exact locations

📖 **See [Korean Maps Setup Guide](docs/KOREAN_MAPS_SETUP.md) for detailed instructions on getting accurate map locations.**

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

# Optional: For accurate Korean address geocoding (recommended)
KAKAO_REST_API_KEY=your_kakao_rest_api_key
```

**Note**: To get accurate map locations for Korean addresses, obtain a free Kakao REST API key at [https://developers.kakao.com/](https://developers.kakao.com/). Without this key, the system will use approximate regional coordinates.

#### 4. Run the Web Interface

```bash
# Run any Python script using uv run
uv run python scripts/run_app.py
```

Open http://localhost:8001 in your browser.

#### 5. Run Command Line Scripts

```bash
# Filter firms
uv run python scripts/run_filter.py

# Search and summarize with options
uv run python scripts/run_summarize.py --dry-run
uv run python scripts/run_summarize.py --limit 10
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

# Optional: For accurate Korean address geocoding (recommended)
KAKAO_REST_API_KEY=your_kakao_rest_api_key
```

**Note**: To get accurate map locations for Korean addresses, obtain a free Kakao REST API key at [https://developers.kakao.com/](https://developers.kakao.com/). Without this key, the system will use approximate regional coordinates.

#### 3. Run the Web Interface

```bash
python scripts/run_app.py
```

Open http://localhost:8001 in your browser.

Available pages:
- 🔧 **Configuration Editor**: `http://localhost:8001/` or `http://localhost:8001/config/firm-summary` - Configure filters, search parameters, summary settings, and categories
- 📊 **Results Viewer**: `http://localhost:8001/view/firm-summary` - View and browse processed firm summaries by category
- 🗺️ **Map Viewer**: `http://localhost:8001/firms` - Interactive map showing firms with subway lines

#### 4. Run Command Line Scripts

```bash
# Filter firms
python scripts/run_filter.py

# Search and summarize with options
python scripts/run_summarize.py --dry-run
python scripts/run_summarize.py --limit 10
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
uv run python scripts/run_filter.py

# With pip (traditional)
python scripts/run_filter.py

# Override with command line
python scripts/run_filter.py --locations 서울 경기 --filter-type contains

# Different input file
python scripts/run_filter.py -i my_firms.csv -o filtered.csv
```

### Search and Summarize

```bash
# Dry run (no API calls)
python scripts/run_summarize.py --dry-run

# Process limited number of firms
python scripts/run_summarize.py --limit 10

# Use custom config
python scripts/run_summarize.py --config my_config.yml
```

### Parse PDF to CSV (New!)

```bash
# Parse PDF with default settings
python scripts/run_pdf_parser_rule.py

# Extract city from location and add as a column
python scripts/run_pdf_parser_rule.py --extract-city-from-location

# Parse custom PDF with column mapping
python scripts/run_pdf_parser_rule.py \
  --pdf data/korean_companies.pdf \
  --output data/korean_companies.csv \
  --columns "번호" "회사명" "상세주소" "도시"

# Rename columns while parsing
python scripts/run_pdf_parser_rule.py \
  --columns "번호:Number" "회사명:Company Name" "소재지:Location" \
  --extract-city-from-location

# For detailed documentation
See [docs/README_PDF_PARSER.md](docs/README_PDF_PARSER.md)
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

## Firm List Data Format

The application works with CSV files containing firm information. **Only 2 columns are required**:

- `업체명` (Company Name) - Required for identification and search
- `소재지` (Location) - Required for filtering and geocoding

All other columns are optional and can be customized for your use case.

### Sample CSV Files

Example CSV files for different scenarios are provided in `data/samples/`:

- `minimal_example.csv` - Just the 2 required columns
- `standard_example.csv` - Common business fields
- `research_institutions.csv` - Universities and labs
- `startups.csv` - Startup companies
- `international.csv` - Global companies
- `manufacturing.csv` - Manufacturing firms
- `healthcare.csv` - Healthcare institutions

### Creating Your Own Firm List

1. Create a CSV file with at least `업체명` and `소재지` columns
2. Add any additional columns relevant to your use case
3. Save with UTF-8 encoding to support Korean characters
4. Use with the filter and search scripts

**See [FIRM_DATA_FORMAT.md](docs/FIRM_DATA_FORMAT.md) for detailed specifications and examples.**

## Configuration

All settings are stored in `config.yml`. You can edit this file directly or use the web interface.

### Using the Dual-Page Interface

The application provides two dedicated pages for managing firm summaries:

#### 1. Configuration Editor (`/` or `/config/firm-summary`)
- **Summary Settings**: Configure output language, format, focus areas, and custom prompts
- **Search Settings**: Set query templates, search depth, and max results
- **Categories**: Define and manage categories with keywords for automatic classification
- **Actions**: Save, reload, or reset configuration to defaults

#### 2. Results Viewer (`/view/firm-summary`)
- **Statistics Dashboard**: View total firms processed and counts per category
- **Category Selection**: Browse firms by category with color-coded cards
- **Search & Filter**: Search firms by name within selected category
- **Summary Display**: View full markdown-rendered summaries with proper formatting

**Navigation**: Both pages include a navigation bar for easy switching between:
- ⚙️ Config Editor
- 📊 View Results
- 🗺️ Map Viewer

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

## Korean Address Geocoding

### Overview

The map viewer supports accurate geocoding of Korean addresses, including both address formats used in South Korea:

- **도로명주소 (Road Name Address)**: Modern address system based on road names (e.g., "서울특별시 강남구 테헤란로 123")
- **지번주소 (Lot Number Address)**: Traditional address system based on land parcel numbers (e.g., "서울특별시 강남구 역삼동 123-45")

### Accurate Location Display

To display exact locations on the map instead of approximate regional coordinates:

1. **Get a Kakao REST API Key** (Free):
   - Visit [https://developers.kakao.com/](https://developers.kakao.com/)
   - Create an account and register an application
   - Get your REST API key from the application dashboard

2. **Set the Environment Variable**:
   ```bash
   export KAKAO_REST_API_KEY=your_api_key_here
   ```
   Or add it to your `.env` file:
   ```
   KAKAO_REST_API_KEY=your_api_key_here
   ```

3. **Regenerate Geocoded Data**:
   ```bash
   uv run python scripts/run_geocoding.py
   ```
   The script will automatically use Kakao Maps API for accurate geocoding.

### Geocoding Methods (in order of preference)

1. **Kakao Maps API** (Most Accurate):
   - Best for Korean addresses
   - Handles both 도로명주소 and 지번주소
   - Provides exact coordinates

2. **Nominatim (OpenStreetMap)** (Fallback):
   - Works for some Korean addresses
   - Less accurate than Kakao for incomplete addresses

3. **Regional Coordinates** (Final Fallback):
   - Uses hardcoded coordinates for major cities and districts
   - Adds random offset to prevent marker overlap
   - Only shows approximate location

### Caching

Geocoding results are cached in `data/geocode_cache.json` to:
- Avoid repeated API calls
- Speed up subsequent runs
- Preserve geocoding results

To force re-geocoding, delete the cache file before running the script.

## File Structure

```
firm_websearch/
├── src/
│   └── firm_analyzer/
│       ├── core/           # Core engine scripts (filter, summarize, geocoding, etc.)
│       ├── web/            # Flask webapp server (app.py, templates, static)
│       ├── utils/          # Helper modules (webpage finder, etc.)
│       └── config.py       # Primary configuration module
├── scripts/                # CLI wrapper scripts (run_app.py, run_filter.py, etc.)
├── config.yml              # Primary configuration file (YAML)
├── docs/                   # Documentation and guides
│   ├── ENGINES_GUIDE.md    # Multi-language guide for all 7 engines
│   ├── FIRM_DATA_FORMAT.md # Guide on CSV data format specifications
│   ├── KOREAN_MAPS_SETUP.md # Detailed Kakao Maps geocoding setup guide
│   ├── SUPABASE_SETUP.md   # Supabase backend deployment guide
│   ├── GEOCODING.md        # Technical explanation of geocoding strategies
│   ├── README_PDF_PARSER.md # Extended PDF parser usage documentation
│   └── README_WEBPAGE_FINDER.md # Webpage finder module documentation
├── frontend/               # Modern Vite + React frontend codebase
├── firm_results/           # Output directory for local JSON/MD summaries
├── data/                   # Data directory (CSV resources and caches)
│   ├── samples/            # Pre-validated sample CSV files
│   └── geocode_cache.json  # Cached address geocoding results
├── pyproject.toml          # Python package definitions
└── README.md               # Main readme documentation
```

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

---

## Engines Guide / 엔진 사용 가이드

For a detailed guide on how each processing and execution engine works, their parameters, and commands to run them via CLI, see **[Engines Guide (docs/ENGINES_GUIDE.md)](docs/ENGINES_GUIDE.md)**.

각 처리 및 실행 엔진의 상세 작동 원리, 파라미터, 명령행 실행 방법 등은 **[엔진 사용 가이드 (docs/ENGINES_GUIDE.md)](docs/ENGINES_GUIDE.md)**를 참고하세요.
