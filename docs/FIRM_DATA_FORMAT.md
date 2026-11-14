# Firm List Data Format Guide

This document explains the column structure required for firm list CSV files to work with the Firm Analyzer application.

## Table of Contents

- [Overview](#overview)
- [Required Columns](#required-columns)
- [Optional Columns](#optional-columns)
- [Column Specifications](#column-specifications)
- [Sample Use Cases](#sample-use-cases)
- [Creating Your Own Firm List](#creating-your-own-firm-list)

## Overview

The Firm Analyzer application is designed to be flexible and work with various types of firm/company data. The application processes CSV files containing firm information, filters them based on configurable criteria, searches for additional information online, and generates summaries.

**Minimum Requirements**: Only 2 columns are absolutely required for the application to function.

## Required Columns

These columns MUST exist in your CSV file for the application to work properly:

| Column Name | Description | Example | Notes |
|------------|-------------|---------|-------|
| `업체명` | Firm/Company name | `"삼성전자(주)"`, `"Google Korea"` | **Required** - Used for search queries and identification |
| `소재지` | Location/Address | `"서울특별시 강남구 테헤란로"` | **Required** - Used for filtering (and for the map, if the CSV is the active list) |

### Why These Columns?

1. **업체명 (Firm Name)**: 
   - Core identifier for the firm
   - Used in web searches to find company information
   - Used in file/folder naming for results
   - Cannot be empty

2. **소재지 (Location)**:
   - Used by location-based filters (e.g., filter firms in Seoul)
   - Used for geocoding and map display, but only for the active list (see the note below)
   - Can contain full or partial addresses
   - Supports both Korean address formats (도로명주소, 지번주소)

## Optional Columns

These columns enhance functionality but are NOT required:

| Column Name | Description | Example | Benefits |
|------------|-------------|---------|----------|
| `연번` | Sequential number | `1`, `2`, `3` | Helps maintain original order |
| `업종구분` | Industry/Business type | `"벤처기업부설연구소"`, `"Technology"` | Additional classification/filtering |
| `25년 배정인원` | Assigned personnel (or any metric) | `"44"`, `"미배정"` | Custom business metrics |
| `관할청` | Jurisdiction/Region | `"서울"`, `"경기"` | Regional grouping |
| Custom columns | Any additional data | `"CEO Name"`, `"Revenue"` | Add any fields relevant to your use case |

## Column Specifications

### Firm Name (`업체명`)

- **Required**: Yes
- **Data Type**: Text/String
- **Character Limit**: No limit (but shorter names work better for display)
- **Encoding**: UTF-8 (supports Korean, English, and other languages)
- **Special Characters**: Allowed (e.g., parentheses, hyphens)
- **Empty Values**: Not allowed

**Examples**:
```csv
업체명
삼성전자(주)
Google Korea LLC
㈜카카오
Naver Corporation
스타트업코리아
```

### Location (`소재지`)

- **Required**: Yes
- **Data Type**: Text/String
- **Format**: Any address format (Korean or international)
- **Completeness**: Can be complete or partial
  - Full: `"서울특별시 강남구 테헤란로 123"`
  - Partial: `"서울특별시 강남구"`
  - Minimal: `"서울"`
- **Empty Values**: Should not be empty (use "Unknown" or "미정" if address unknown)

**Examples**:
```csv
소재지
서울특별시 강남구 테헤란로
경기도 성남시 분당구
부산광역시
대전광역시 유성구 대학로
San Francisco, CA
```

**Geocoding Behavior**:
- Kakao Maps API: Best for Korean addresses (requires API key)
- Nominatim: Works for international addresses
- Fallback: Uses regional coordinates if geocoding fails

> [!NOTE]
> The map only shows the **active list**: `firm-geocode` reads the list that
> `firm-roster list` marks with `*`, never a CSV you pass to `firm-filter --input`.
> To put your own CSV on the map, save it in `data/`, make it the active list
> with `uv run firm-roster activate my_companies.csv`, then run `firm-geocode`
> (see [GEOCODING.md](GEOCODING.md)). The active list is also the filter's
> default input.

### Optional Columns

You can add ANY additional columns that are relevant to your use case. The application will:
- Read all columns from the CSV
- Preserve them during filtering
- Make them available in the filtered output
- Not use them for search or summary: the search query only uses `업체명`
  (through `search.query_template` in `config.yml`)

## Sample Use Cases

### 1. Research Institution List

**Scenario**: List of universities and research labs for recruitment purposes.

**Required Columns**:
```csv
업체명,소재지
서울대학교,서울특별시 관악구 관악로
한국과학기술원,대전광역시 유성구 대학로
```

**Enhanced Version** (with optional columns):
```csv
업체명,소재지,기관유형,연구분야,웹사이트
서울대학교,서울특별시 관악구 관악로,대학교,종합,https://www.snu.ac.kr
한국과학기술원,대전광역시 유성구 대학로,특수대학,과학기술,https://www.kaist.ac.kr
```

### 2. Startup Companies

**Scenario**: Tracking startup companies for investment research.

**Minimal Version**:
```csv
업체명,소재지
토스뱅크,서울특별시 강남구
당근마켓,서울특별시 강남구
```

**Enhanced Version**:
```csv
업체명,소재지,설립연도,업종,투자단계,직원수
토스뱅크,서울특별시 강남구 테헤란로,2019,핀테크,Series C,200+
당근마켓,서울특별시 강남구,2015,커머스,Series E,300+
```

### 3. Global Tech Companies

**Scenario**: International tech companies with offices in Korea.

**Minimal Version**:
```csv
업체명,소재지
Google Korea,Seoul
Microsoft Korea,Seoul
```

**Enhanced Version**:
```csv
업체명,소재지,본사위치,직원규모,주요사업
Google Korea,서울특별시 강남구,Mountain View US,500+,검색 및 광고
Microsoft Korea,서울특별시 종로구,Redmond US,300+,소프트웨어
```

### 4. Manufacturing Companies

**Scenario**: Manufacturing companies for supply chain analysis.

**Enhanced Version**:
```csv
업체명,소재지,제품분류,생산규모,인증
삼성전자,경기도 수원시,전자제품,대기업,ISO 9001
LG전자,서울특별시 영등포구,전자제품,대기업,ISO 9001
```

### 5. Healthcare Institutions

**Scenario**: Hospitals and clinics for healthcare research.

**Enhanced Version**:
```csv
업체명,소재지,기관종류,병상수,전문분야
서울대학교병원,서울특별시 종로구,종합병원,1800,종합의료
세브란스병원,서울특별시 서대문구,종합병원,2000,종합의료
```

## Creating Your Own Firm List

### Step 1: Choose Your Columns

Decide which data is relevant for your use case:

1. **Always include**: `업체명`, `소재지`
2. **Consider adding**: Industry type, size, contact info, metrics
3. **Custom fields**: Add any domain-specific data

### Step 2: Create the CSV File

Use any tool (Excel, Google Sheets, Python, etc.) to create a CSV file:

```csv
업체명,소재지,업종,규모
회사A,서울특별시,IT,중소기업
회사B,경기도 성남시,제조,대기업
회사C,부산광역시,서비스,스타트업
```

**Important CSV Guidelines**:
- Use UTF-8 encoding to support Korean characters
- First row must contain column headers
- Use commas (`,`) as separators
- Enclose fields with commas in quotes: `"서울특별시, 강남구"`

### Step 3: Configure Filters

Edit `config.yml` to specify which column to filter on:

```yaml
filters:
  location:
    enabled: true
    column: 소재지
    type: contains
    values:
    - 서울
    - 경기
```

**Filter Column Options**:
- Use `"소재지"` for location-based filtering
- Use any other column name for custom filtering
- Example: `column: 업종` to filter by industry type

### Step 4: Run the Application

```bash
# 1. Place your CSV file in the project directory
# For example: my_companies.csv

# 2. Filter the firms (a relative --output goes under data/: this writes data/filtered.csv)
uv run firm-filter --input my_companies.csv --output filtered.csv

# 3. Search and summarize (reads data/filtered.csv)
uv run firm-summarize --input filtered.csv

# Or use the web interface. Its pipeline always starts from the active list,
# so save the CSV in data/ and activate it first:
uv run firm-roster activate my_companies.csv
uv run firm-app
# Open http://localhost:8001
```

## Configuration Tips

### Custom Column Filtering

You can filter on ANY column in your CSV (in `config.yml`):

```yaml
filters:
  location:
    enabled: true
    column: 업종
    type: contains
    values:
    - IT
    - 소프트웨어
```

### Multiple Use Cases

Create different CSV files for different scenarios. The samples in `data/samples/` are laid out this way:

```
data/samples/
  ├── research_institutions.csv      # Universities and labs
  ├── startups.csv                    # Startup companies
  ├── manufacturing.csv               # Manufacturing firms
  ├── healthcare.csv                  # Hospitals
  └── international.csv               # International tech companies
```

Then run the filter script with different inputs (this writes `data/filtered_startups.csv`):

```bash
uv run firm-filter --input data/samples/startups.csv --output filtered_startups.csv
```

## Common Patterns

### Pattern 1: Government/Public Data

When working with government datasets (like 전문연구요원 인원배정):

```csv
연번,업종구분,업체명,소재지,배정인원,관할청
1,연구소,한국과학기술원,대전광역시,415,대전.충남
```

### Pattern 2: Business Directory

When working with business directories:

```csv
업체명,소재지,전화번호,대표자,설립일
삼성전자,경기도 수원시,02-1234-5678,홍길동,1969-01-13
```

### Pattern 3: Minimal Tracking

When you just need to track and research companies:

```csv
업체명,소재지
회사A,서울
회사B,부산
```

## Frequently Asked Questions

### Q: Can I use English column names?

**A**: The application expects Korean column names (`업체명`, `소재지`) by default. However, you can:

1. Rename columns in your CSV to match:
   ```python
   df = pd.read_csv('your_file.csv')
   df.rename(columns={'Company Name': '업체명', 'Location': '소재지'}, inplace=True)
   df.to_csv('converted.csv', index=False)
   ```

2. Or rename the columns on import: `uv run firm-roster import your.csv --year 2027` accepts 회사명/기업명 for 업체명 and 주소 for 소재지.

### Q: What if some firms don't have addresses?

**A**: You can use placeholder values:
- `"미정"` (undecided)
- `"Unknown"`
- `"Seoul"` (city name if only city is known)

The application will still process these firms, but geocoding may be less accurate.

### Q: How many firms can I process?

**A**: The application can handle:
- **Filtering**: Unlimited (CSV processing is fast)
- **Search/Summary**: Limited by API quotas
  - Tavily API: Check your plan limits
  - Your LLM provider (OpenAI, Claude, Gemini or GitHub Models): rate limits and quotas apply. A spent quota stops the run; already processed firms are skipped on the next run.
  - Recommendation: Process in batches using `--limit` parameter

### Q: Can I have duplicate firm names?

**A**: Yes, but be aware:
- Results are organized by sanitized firm name
- Only the first firm with a given name is processed. Once its folder exists in any category, later rows with the same name are skipped as "already processed", in this run and in later runs.
- Consider adding unique identifiers in the firm name if needed

### Q: What about non-Korean companies?

**A**: Fully supported! The application works with:
- Korean company names and addresses
- English company names and addresses
- Mixed Korean-English names
- International addresses (though Korean addresses work best for geocoding)

## Sample CSV Files

Sample CSV files are provided in the `data/samples/` directory:

- `minimal_example.csv` - Minimal 2-column format
- `standard_example.csv` - Standard format with common optional columns
- `research_institutions.csv` - Example for research institutions
- `startups.csv` - Example for startup companies
- `manufacturing.csv` - Example for manufacturing companies
- `healthcare.csv` - Example for hospitals
- `international.csv` - Example with international companies

## Additional Resources

- [Main README](../README.md) - General application usage
- [config.example.yml](../config.example.yml) - Configuration example (copy it to `config.yml` to edit)
- [filter.py](../src/firm_analyzer/core/filter.py) - Filtering (`firm-filter`)
- [summarize.py](../src/firm_analyzer/core/summarize.py) - Search and summarize (`firm-summarize`)
- [PDF Parser Guide](README_PDF_PARSER.md) - Converting PDF to CSV

## Support

For questions or issues:
- Check existing sample CSV files in `data/samples/`
- Review the main [README.md](../README.md)
- Open a GitHub issue
