# Firm Summary Tools

This directory contains utility scripts for processing and analyzing research personnel allocation data.

## Core Utilities

### 1. PDF to CSV Parser (`parse_pdf_to_csv_extended.py`)

Flexible PDF table parser with column mapping, city extraction, and multi-format support.

**Features:**
- Flexible column mapping and renaming
- Automatic city extraction from Korean addresses
- Smart header detection and fuzzy column matching
- Supports various PDF table layouts

**Basic Usage:**
```bash
# Parse with default settings
python parse_pdf_to_csv_extended.py

# Extract city from location field
python parse_pdf_to_csv_extended.py --extract-city-from-location

# Custom PDF with column mapping
python parse_pdf_to_csv_extended.py \
  --pdf data/custom.pdf \
  --output data/output.csv \
  --columns "번호" "회사명" "소재지" "도시"
```

**See [README_PDF_PARSER.md](../docs/README_PDF_PARSER.md) for detailed documentation.**

### 2. Map Data Generator (`generate_firms_data.py`)

Converts CSV firm data to JavaScript format with geocoded coordinates for map display.

**Features:**
- Multi-tier geocoding (Kakao API, Nominatim, fallback)
- Geocoding cache to avoid repeated API calls
- Supports both 도로명주소 and 지번주소
- Handles incomplete Korean addresses intelligently

**Usage:**
```bash
# Interactive mode
cd firm_summary
python generate_firms_data.py

# Use API geocoding (requires KAKAO_REST_API_KEY)
python generate_firms_data.py --use-api

# Use fallback coordinates only
python generate_firms_data.py --no-api
```

**See [GEOCODING.md](../docs/GEOCODING.md) and [KOREAN_MAPS_SETUP.md](../docs/KOREAN_MAPS_SETUP.md) for detailed setup.**

### 3. Firm Webpage Finder (`find_firm_webpage.py`)

Automatically finds and verifies firm official webpages using Tavily search and LLM verification.

**Features:**
- Tavily search integration
- GPT-4 based verification with confidence scoring
- Returns reasoning for webpage selection
- Integrated into main search/summarize workflow

**Standalone Usage:**
```bash
python find_firm_webpage.py "카카오"
```

**Integration:**
```python
from find_firm_webpage import find_firm_webpage, initialize_clients

tavily_client, openai_client = initialize_clients()
result = find_firm_webpage("카카오", tavily_client, openai_client)
```

**See [README_WEBPAGE_FINDER.md](../docs/README_WEBPAGE_FINDER.md) for detailed documentation.**

## Shell Scripts

### example_pdf_parsing.sh

Example commands demonstrating various PDF parsing scenarios.

## Dependencies

All dependencies are in the main `requirements.txt`:
```bash
pip install -r ../requirements.txt
```

Key packages:
- `pdfplumber` - PDF table extraction
- `geopy` - Address geocoding
- `requests` - HTTP requests for Kakao API
- `tavily` - Web search API
- `openai` - LLM integration

## Output Files

Scripts generate various output files:

- **CSV files**: `data/*.csv` - Parsed and filtered firm data
- **Map data**: `../webapp/static/js/firms_data.js` - Geocoded JavaScript data
- **Geocode cache**: `../data/geocode_cache.json` - Cached geocoding results

## Related Documentation

- [Main README](../README.md) - Project overview and setup
- [KOREAN_MAPS_SETUP.md](../docs/KOREAN_MAPS_SETUP.md) - Kakao Maps API setup guide
- [ENGINES_GUIDE.md](../docs/ENGINES_GUIDE.md) - Multi-engine CLI runner guide
