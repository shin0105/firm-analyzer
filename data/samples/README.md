# Sample Firm List CSV Files

This directory contains sample CSV files demonstrating different use cases and column structures for the Firm Analyzer application.

## Quick Start

Try any of these samples with the application:

```bash
# Filter a sample file
python filter_firms.py --input data/samples/startups.csv --output filtered_startups.csv

# Use with the web interface
# 1. Copy a sample file to the main directory
cp data/samples/minimal_example.csv my_firms.csv

# 2. Update config.json to point to your file
# 3. Run the web app
python app.py
```

## Available Samples

### 1. minimal_example.csv
**Scenario**: Absolute minimum - just company name and location

**Columns**: 
- `업체명` (Company Name) - Required
- `소재지` (Location) - Required

**Use Case**: Quick start with minimal data requirements

**Example**:
```csv
업체명,소재지
삼성전자(주),경기도 수원시 영통구
네이버(주),경기도 성남시 분당구
```

### 2. standard_example.csv
**Scenario**: Standard business dataset with common fields

**Columns**:
- `연번` (Number)
- `업종구분` (Industry Type)
- `업체명` (Company Name) - Required
- `소재지` (Location) - Required
- `직원수` (Employee Count)
- `관할청` (Jurisdiction)

**Use Case**: General business analysis with classification and metrics

**Example**:
```csv
연번,업종구분,업체명,소재지,직원수,관할청
1,대기업,삼성전자(주),경기도 수원시 영통구 삼성로 129,100000,경기
6,벤처기업,토스뱅크(주),서울특별시 강남구 테헤란로 131,500,서울
```

### 3. research_institutions.csv
**Scenario**: Universities and research laboratories

**Columns**:
- `연번` (Number)
- `기관유형` (Institution Type)
- `업체명` (Institution Name) - Required
- `소재지` (Location) - Required
- `연구분야` (Research Field)
- `학생수` (Student Count)

**Use Case**: Academic and research institution analysis

**Example**:
```csv
연번,기관유형,업체명,소재지,연구분야,학생수
1,특수대학,한국과학기술원,대전광역시 유성구 대학로 291,과학기술,11000
5,종합대학,서울대학교,서울특별시 관악구 관악로 1,종합,28000
```

### 4. startups.csv
**Scenario**: Startup companies for investment research

**Columns**:
- `업체명` (Company Name) - Required
- `소재지` (Location) - Required
- `설립연도` (Founded Year)
- `업종` (Industry)
- `투자단계` (Investment Stage)
- `직원수` (Employee Count)
- `주요기술` (Core Technology)

**Use Case**: Startup ecosystem analysis and investor research

**Example**:
```csv
업체명,소재지,설립연도,업종,투자단계,직원수,주요기술
토스뱅크(주),서울특별시 강남구 테헤란로,2019,핀테크,Series E,500+,금융플랫폼
당근마켓(주),서울특별시 강남구,2015,커머스,Series E,300+,지역기반 거래
```

### 5. international.csv
**Scenario**: International companies with Korean offices

**Columns**:
- `업체명` (Company Name) - Required
- `소재지` (Korean Location) - Required
- `본사위치` (HQ Location)
- `직원규모` (Employee Size)
- `주요사업` (Main Business)
- `설립연도` (Founded Year)

**Use Case**: Global company analysis with local presence

**Example**:
```csv
업체명,소재지,본사위치,직원규모,주요사업,설립연도
Google Korea,서울특별시 강남구 테헤란로,Mountain View CA USA,500+,검색 및 광고,1998
Microsoft Korea,서울특별시 종로구 종로,Redmond WA USA,300+,소프트웨어,1975
```

### 6. manufacturing.csv
**Scenario**: Manufacturing companies for supply chain analysis

**Columns**:
- `연번` (Number)
- `업체명` (Company Name) - Required
- `소재지` (Location) - Required
- `제품분류` (Product Category)
- `생산규모` (Production Scale)
- `인증` (Certification)
- `연매출` (Annual Revenue)

**Use Case**: Manufacturing sector analysis with metrics

**Example**:
```csv
연번,업체명,소재지,제품분류,생산규모,인증,연매출
1,삼성전자(주),경기도 수원시,전자제품,대기업,ISO 9001,280조원
4,포스코(주),경상북도 포항시,철강,대기업,ISO 9001,70조원
```

### 7. healthcare.csv
**Scenario**: Healthcare institutions and hospitals

**Columns**:
- `연번` (Number)
- `업체명` (Institution Name) - Required
- `소재지` (Location) - Required
- `기관종류` (Institution Type)
- `병상수` (Bed Count)
- `전문분야` (Specialty)
- `설립연도` (Founded Year)

**Use Case**: Healthcare sector research and analysis

**Example**:
```csv
연번,업체명,소재지,기관종류,병상수,전문분야,설립연도
1,서울대학교병원,서울특별시 종로구 대학로,종합병원,1800,종합의료,1978
4,삼성서울병원,서울특별시 강남구 일원로,종합병원,1900,종합의료,1994
```

## How to Use These Samples

### 1. Test the Application

```bash
# Try filtering by location
python filter_firms.py \
  --input data/samples/standard_example.csv \
  --locations 서울 \
  --output test_seoul.csv

# See what gets filtered
cat test_seoul.csv
```

### 2. Understand Column Requirements

Open any sample file to see:
- Which columns are required (`업체명`, `소재지`)
- Which columns are optional (everything else)
- How to structure your data

### 3. Create Your Own CSV

1. Choose the sample closest to your use case
2. Copy and modify it with your data
3. Keep the `업체명` and `소재지` columns
4. Add any additional columns you need

### 4. Customize Configuration

If you add custom columns, you can filter on them:

```json
{
  "filters": {
    "location": {
      "enabled": true,
      "column": "업종",
      "type": "contains",
      "values": ["핀테크", "IT"]
    }
  }
}
```

## Column Name Reference

### Required Columns (Must Use These Names)

| Korean | English | Note |
|--------|---------|------|
| `업체명` | Company Name | Used by scripts to identify firms |
| `소재지` | Location | Used by filters and geocoding |

### Optional Column Name Examples

You can name optional columns anything you want. Common examples:

| Korean | English | Purpose |
|--------|---------|---------|
| `연번` | Number | Ordering |
| `업종구분` | Industry | Classification |
| `직원수` | Employee Count | Size metric |
| `관할청` | Jurisdiction | Region grouping |
| `설립연도` | Founded Year | Age metric |
| `투자단계` | Investment Stage | Maturity |
| `주요기술` | Core Tech | Technology focus |
| `연매출` | Revenue | Financial metric |

## Tips

1. **UTF-8 Encoding**: Always save your CSV files with UTF-8 encoding to support Korean characters
2. **Excel Users**: When saving from Excel, choose "CSV UTF-8" format
3. **Comma in Data**: If your data contains commas, enclose the field in quotes:
   ```csv
   "서울특별시, 강남구",1000
   ```
4. **Empty Fields**: Leave optional fields empty if you don't have data:
   ```csv
   업체명,소재지,직원수
   회사A,서울,100
   회사B,부산,
   ```

## Testing Your CSV

Before processing a large file:

```bash
# Test with just 5 rows
head -6 your_file.csv > test.csv  # Include header + 5 rows

# Test filtering
python filter_firms.py --input test.csv --output test_filtered.csv

# Test search (dry run - no API calls)
python search_summarize.py --input test_filtered.csv --dry-run --limit 2
```

## Validation Checklist

Before using your CSV file, check:

- [ ] File is saved with UTF-8 encoding
- [ ] First row contains column headers
- [ ] Column `업체명` exists and has no empty values
- [ ] Column `소재지` exists
- [ ] All rows have the same number of columns
- [ ] Commas in data are properly quoted
- [ ] No trailing commas at end of rows

## Additional Resources

- [FIRM_DATA_FORMAT.md](../../docs/FIRM_DATA_FORMAT.md) - Complete data format guide
- [README.md](../../README.md) - Main application documentation
- [config.yml](../../config.yml) - Configuration examples

## Questions?

If you need help:
1. Check the main [FIRM_DATA_FORMAT.md](../../docs/FIRM_DATA_FORMAT.md) guide
2. Look at the sample files in this directory
3. Review the main [README.md](../../README.md)
4. Open a GitHub issue with your question
