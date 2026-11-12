# PDF to CSV Parser - Extended Features

## Overview

The rule-based PDF parser (`firm-parse-pdf`, `src/firm_analyzer/core/pdf_parser_rule.py`) provides a flexible way to extract table data from various PDF formats and convert them to CSV files. It's particularly useful for parsing Korean company lists with different column structures.

## Key Features

1. **Flexible Column Mapping**: Map PDF columns to custom CSV column names
2. **Automatic City Extraction**: Extract city names from Korean address strings
3. **Smart Header Detection**: Automatically detect table headers in PDFs
4. **Fuzzy Column Matching**: Match columns even if names don't exactly match
5. **Multiple PDF Format Support**: Works with various table layouts

## Usage Examples

### Example 1: A 인원배정 PDF

> To import a new yearly list for the pipeline, use `firm-roster import` (or the
> **전문연 명단 관리** page) instead: it calls this parser, then normalises the
> columns, checks the row count, compares with the previous list and makes the
> new list active. See the README's "Updating the 전문연 list" section.

Parse a research personnel allocation PDF with the default columns:

```bash
uv run firm-parse-pdf --pdf data/2026_전문연구요원_인원배정.pdf
```

This writes `data/2026_전문연구요원_인원배정_parsed.csv` with the columns:
- 연번 (Number)
- 업종구분 (Industry Type)
- 업체명 (Company Name)
- 소재지 (Location)
- 배정인원 (Allocation; matches the "25년 배정인원", "26년 배정인원", … header of any year)
- 관할청 (Jurisdiction)

### Example 2: Extract City from Location

Automatically add a city column extracted from the location field:

```bash
uv run firm-parse-pdf --pdf data/2026_전문연구요원_인원배정.pdf --extract-city-from-location
```

Output CSV will include an additional "도시" (City) column with extracted city names:
- `서울특별시 강남구 테헤란로 123` → `서울특별시`
- `경기도 수원시 영통구 삼성로 129` → `수원시`
- `부산광역시 해운대구 센텀중앙로 79` → `부산광역시`

### Example 3: Custom PDF with Column Mapping

Parse a Korean company list PDF with custom columns:

```bash
uv run firm-parse-pdf \
    --pdf data/korean_companies.pdf \
    --output data/korean_companies.csv \
    --columns "번호" "회사명" "상세주소" "도시"
```

### Example 4: Column Renaming

Map source columns to different output column names:

```bash
uv run firm-parse-pdf \
    --pdf data/firms.pdf \
    --output data/firms.csv \
    --columns "번호:Number" "회사명:Company Name" "소재지:Detail Location" "도시:City"
```

This will:
- Look for "번호" in the PDF and name it "Number" in CSV
- Look for "회사명" in the PDF and name it "Company Name" in CSV
- And so on...

### Example 5: Combining Options

Extract city from location and use custom settings:

```bash
uv run firm-parse-pdf \
    --pdf data/company_directory.pdf \
    --output data/parsed_directory.csv \
    --columns "기업명" "주소" "전화번호" \
    --extract-city-from-location \
    --min-columns 2
```

## Command Line Arguments

| Argument | Short | Description | Default |
|----------|-------|-------------|---------|
| `--pdf` | `-p` | Path to input PDF file (required) | — |
| `--output` | `-o` | Path to output CSV file | `<pdf name>_parsed.csv` next to the PDF |
| `--columns` | `-c` | Column names (space-separated) | Default columns |
| `--extract-city-from-location` | | Extract city from location field | False |
| `--min-columns` | | Minimum non-empty columns for valid row | 3 |

## Column Format

When using `--columns`, you can specify:

1. **Simple column names**: Just the column name
   ```bash
   --columns "번호" "회사명" "주소"
   ```

2. **With renaming**: Use `source:target` format
   ```bash
   --columns "번호:Number" "회사명:Company Name" "주소:Address"
   ```

## City Extraction Feature

The `--extract-city-from-location` flag automatically extracts city names from Korean address strings using pattern matching:

**Supported formats:**
- 특별시 (Special City): e.g., `서울특별시`, `세종특별자치시`
- 광역시 (Metropolitan City): e.g., `부산광역시`, `대구광역시`
- 특별자치도 (Special Self-Governing Province): e.g., `제주특별자치도`
- 도 + 시 (Province + City): e.g., `경기도 수원시` → extracts `수원시`
- 시 (City): e.g., `수원시`

**Examples:**
```
Input: "서울특별시 강남구 테헤란로 123"
Output: "서울특별시"

Input: "경기도 수원시 영통구 삼성로 129"
Output: "수원시"

Input: "제주특별자치도 제주시 첨단로 242"
Output: "제주시"
```

## Testing with Korean Company Lists

### Common Sources for Korean Company PDFs:

1. **전문연구요원 인원배정** (Research Personnel Allocation)
   - Official government PDF with research institutions
   - Format: 연번, 업종구분, 업체명, 소재지, 배정인원, 관할청

2. **벤처기업 확인서** (Venture Company Certification)
   - Lists of certified venture companies
   - Format varies by year and issuing organization

3. **이노비즈 인증기업** (Innobiz Certified Companies)
   - Innovative small and medium businesses
   - Format: 기업명, 대표자, 주소, 인증일

4. **코스닥/코스피 상장사** (KOSDAQ/KOSPI Listed Companies)
   - Publicly traded companies
   - Format: 회사명, 종목코드, 업종, 소재지

### Creating Test Data

For testing, you can:
1. Find publicly available Korean company list PDFs
2. Use the 인원배정 PDFs in `data/`
3. Create your own using spreadsheet software (Export to PDF)

## Technical Details

### How It Works

1. **PDF Parsing**: Uses `pdfplumber` to extract tables from PDF pages
2. **Header Detection**: Scans first few rows to identify table headers
3. **Column Matching**: Fuzzy matching to align expected columns with found headers
4. **Data Extraction**: Extracts and cleans cell data
5. **City Extraction**: Uses regex patterns to extract city from location strings
6. **CSV Generation**: Writes formatted CSV with specified columns

### Smart Features

- **Automatic whitespace normalization**: Cleans up cell text
- **Empty row filtering**: Skips rows with insufficient data
- **Repeated header detection**: Ignores duplicate headers in multi-page PDFs
- **Flexible column order**: Doesn't require columns in specific order

## Troubleshooting

### Problem: No data extracted
- Check if PDF has actual tables (not just text or images)
- Try reducing `--min-columns` value
- Verify PDF is not scanned image (requires OCR preprocessing)

### Problem: Wrong columns extracted
- Check column names in PDF with `pdfplumber` manually
- Use exact column names from PDF in `--columns` argument
- Try without `--columns` to see what's being extracted

### Problem: City extraction not working
- Ensure location column contains Korean address format
- Check that location column is properly identified
- Korean addresses should start with administrative division

## Future Enhancements

Potential improvements:
- OCR support for scanned PDFs
- More language support (not just Korean)
- GUI interface for column mapping
- Batch processing multiple PDFs
- Export to other formats (JSON, Excel)
- Address standardization and validation
- Duplicate detection and merging

## Dependencies

- `pdfplumber`: PDF table extraction
- `pandas`: Data manipulation (optional, for advanced features)
- Python 3.7+

Install dependencies:
```bash
pip install pdfplumber
```

## See Also

- `parse_pdf_to_csv.py`: Original simpler version
- `firm-filter`: Filter extracted data
- `firm-summarize`: Enrich data with web search
