# Engines Guide / 엔진 사용 가이드

This document provides a comprehensive overview of the different processing and execution engines within the **Firm Analyzer** system. It details their purpose, how they fit into the workflow, and instructions on how to run them via the command line in both **English** and **Korean**.

본 문서는 **Firm Analyzer** 시스템의 다양한 처리 및 실행 엔진에 대한 종합적인 개요를 제공합니다. 각 엔진의 목적, 워크플로우에서의 역할, 그리고 명령행(CLI)에서 실행하는 방법을 **영어**와 **한국어**로 작성하였습니다.

---

## Table of Contents / 목차
1. [PDF Parsing Engine / PDF 파싱 엔진](#1-pdf-parsing-engine--pdf-파싱-엔진)
2. [Filtering Engine / 필터링 엔진](#2-filtering-engine--필터링-엔진)
3. [Web Search & Summarization Engine / 웹 검색 및 요약 엔진](#3-web-search--summarization-engine--웹-검색-및-요약-엔진)
4. [Firm Webpage Finder / 회사 웹페이지 검색기](#4-firm-webpage-finder--회사-웹페이지-검색기)
5. [Geocoding & Map Data Generator / 지오코딩 및 지도 데이터 생성기](#5-geocoding--map-data-generator--지오코딩-및-지도-데이터-생성기)
6. [Supabase Sync Engine / Supabase 동기화 엔진](#6-supabase-sync-engine--supabase-동기화-엔진)
7. [Web Application Engine / 웹 애플리케이션 서비스](#7-web-application-engine--웹-애플리케이션-서비스)

---

## 1. PDF Parsing Engine / PDF 파싱 엔진

The PDF Parsing Engine converts official government or company PDF lists (such as the Korean research personnel allocation PDF) into structured CSV files. It supports two different approaches:
1. **Rule-Based Extraction** (using `pdfplumber` to extract tables programmatically).
2. **LLM-Based Extraction** (using Gemini/OpenAI vision models to parse unstructured or complex tables).

PDF 파싱 엔진은 공식 정부 문서 또는 기업 PDF 목록(예: 전문연구요원 인원배정 현황 PDF)을 구조화된 CSV 파일로 변환합니다. 두 가지 방식을 지원합니다:
1. **규칙 기반 추출** (`pdfplumber`를 사용하여 표 구조를 프로그래밍 방식으로 추출).
2. **LLM 기반 추출** (Gemini/OpenAI 비전 모델을 사용하여 구조화되지 않거나 복잡한 표 분석).

### Run Instructions / 실행 방법

#### A. Rule-Based Parser (규칙 기반 파서)
This script parses tables using programmatic layout rules and supports Korean city extraction and column renaming.
이 스크립트는 표 레이아웃 규칙을 통해 분석하며, 주소에서 한국 도시명 추출 및 열 이름 변경을 지원합니다.

```bash
# Using UV (Recommended / UV 사용 권장)
uv run python scripts/run_pdf_parser_rule.py [options]

# Using standard Python (일반 파이썬 사용)
python scripts/run_pdf_parser_rule.py [options]
```

**Common Examples / 자주 쓰는 예시:**
```bash
# 1. Parse with default settings (기본 설정으로 파싱)
uv run python scripts/run_pdf_parser_rule.py

# 2. Extract city name from address column (주소 열에서 도시명 자동 추출 추가)
uv run python scripts/run_pdf_parser_rule.py --extract-city-from-location

# 3. Parse custom PDF with custom columns (사용자 정의 PDF 및 열 지정)
uv run python scripts/run_pdf_parser_rule.py \
  --pdf data/my_firms.pdf \
  --output data/my_firms.csv \
  --columns "번호" "회사명" "소재지" "관할청"

# 4. Map and rename columns during parsing (파싱 중 열 이름 변경 매핑)
uv run python scripts/run_pdf_parser_rule.py \
  --columns "번호:Number" "회사명:Company Name" "소재지:Location"
```

**Arguments / 옵션:**
- `-p`, `--pdf`: Input PDF path (required)
- `-o`, `--output`: Output CSV path (Default: `<pdf name>_parsed.csv` next to the PDF)

To import a yearly 인원배정 list for the pipeline, use `uv run firm-roster import <pdf> --year <year>`
(or the **전문연 명단 관리** page), which wraps this parser. / 파이프라인용 연도별 명단은
`firm-roster import`(또는 **전문연 명단 관리** 화면)로 가져오세요.
- `-c`, `--columns`: Space-separated column list or mapping format `source:target`
- `--extract-city-from-location`: Extracts city division (e.g. `서울특별시`, `수원시`) into a new `도시` column
- `--min-columns`: Minimum non-empty fields to identify a row as valid (Default: `3`)

---

#### B. LLM-Based Parser (LLM 기반 파서)
This engine is integrated into the web UI for processing uploaded PDFs. It can also be run inside a Python script using the dynamic API.
이 엔진은 웹 UI와 연동되어 업로드된 PDF를 분석합니다. 파이썬 스크립트 내부에서 동적으로 호출할 수도 있습니다.

*Requires API Key in `.env` / `.env` 파일에 API 키 설정 필요:*
```env
GEMINI_API_KEY=your_gemini_key
# OR / 또는
OPENAI_API_KEY=your_openai_key
```

**Usage inside Python / 파이썬 내부 사용 예시:**
```python
from pdf_parser import parse_pdf_to_csv
output_csv = parse_pdf_to_csv("data/my_document.pdf", provider="gemini") # or "openai"
```

---

## 2. Filtering Engine / 필터링 엔진

Filters raw company CSV datasets using configured location parameters or custom criteria defined in `config.yml`. It ensures you only process companies in target regions, reducing API costs in subsequent search steps.

설정 파일(`config.yml`)에 지정된 위치 매개변수 또는 사용자 정의 기준을 기반으로 원본 기업 CSV 데이터셋을 필터링합니다. 타겟 지역의 기업들만 선별함으로써 후속 웹 검색 단계의 API 비용을 절감합니다.

### Run Instructions / 실행 방법

```bash
# Using UV (Recommended / UV 사용 권장)
uv run python scripts/run_filter.py [options]

# Using standard Python (일반 파이썬 사용)
python scripts/run_filter.py [options]
```

**Common Examples / 자주 쓰는 예시:**
```bash
# 1. Filter using settings from config.yml (config.yml 설정대로 필터링)
uv run python scripts/run_filter.py

# 2. Override location filter via command line (명령행으로 특정 지역 지정 필터링)
uv run python scripts/run_filter.py --locations 서울 경기 --filter-type contains

# 3. Specify custom input and output files (입출력 파일명 직접 지정)
uv run python scripts/run_filter.py -i data/custom_companies.csv -o data/filtered.csv
```

**Arguments / 옵션:**
- `-i`, `--input`: Input CSV file path (Default: the active 인원배정 list, see `uv run firm-roster list`)
- `-o`, `--output`: Output CSV file path (Default: `data/filtered_firms.csv`, the file summarize reads by default)
- `-l`, `--locations`: One or more location values to filter on (overrides config)
- `--column`: CSV column name to apply filter on (Default: `소재지`)
- `--filter-type`: Pattern matching strategy (`contains`, `exact`, `startswith`)

---

## 3. Web Search & Summarization Engine / 웹 검색 및 요약 엔진

This engine runs web searches for each company using Tavily and feeds the results to the selected LLM (OpenAI, Claude, Gemini or GitHub Models) to generate structured markdown summaries. Results are stored in individual subdirectories grouped by industry categories. Every `summary.md` starts with an AI-generated notice and ends with the list of sources it was built from (see [DISCLAIMER.md](../DISCLAIMER.md)).

Tavily를 통해 각 기업에 관한 웹 검색을 수행하고, 선택한 LLM(OpenAI, Claude, Gemini, GitHub Models)으로 구조화된 마크다운 요약문을 만듭니다. 결과물은 업종 카테고리별 하위 디렉토리에 저장되며, 모든 `summary.md`에는 AI 생성 안내와 근거가 된 출처 목록이 함께 기록됩니다.

*Requires API Key in `.env` / `.env` 파일에 API 키 설정 필요:*
```env
TAVILY_API_KEY=your_tavily_key
LLM_PROVIDER=openai          # openai | claude | gemini | github
OPENAI_API_KEY=your_openai_key
```

### Run Instructions / 실행 방법

```bash
# Using UV (Recommended / UV 사용 권장)
uv run python scripts/run_summarize.py [options]

# Using standard Python (일반 파이썬 사용)
python scripts/run_summarize.py [options]
```

**Common Examples / 자주 쓰는 예시:**
```bash
# 1. Test search query structure without making API calls (API 호출 없이 쿼리 구조 확인 - 드라이런)
uv run python scripts/run_summarize.py --dry-run

# 2. Run summarization for only the first 5 firms (처음 5개 기업만 요약 생성 진행)
uv run python scripts/run_summarize.py --limit 5

# 3. Process a different input file (다른 입력 파일로 실행)
uv run python scripts/run_summarize.py --input data/my_firms.csv
```

**Arguments / 옵션:**
- `-i`, `--input`: Input filtered CSV file (Default: `data/filtered_firms.csv`, the filter's output)
- `-o`, `--output-dir`: Output directory path (Default: defined in config as `firm_results/`)
- `--dry-run`: Validates input and logs queries without performing live web search or LLM generation
- `--limit`: Limits the number of firms processed in a single run (useful for testing and budget control)

---

## 4. Firm Webpage Finder / 회사 웹페이지 검색기

Performs a focused search using Tavily to find a company's official website URL, extracts webpage metadata, and uses an LLM to evaluate the confidence level and verify that the website belongs to the specified company.

Tavily 검색을 활용해 기업의 공식 웹사이트 URL을 찾고, 웹페이지 메타데이터를 추출한 뒤 LLM을 통해 신뢰도 점수를 부여하여 해당 웹사이트가 입력된 기업의 것이 맞는지 검증합니다.

*Requires / 필수 API 키:* `TAVILY_API_KEY` and the key of the selected LLM provider

### Run Instructions / 실행 방법

```bash
# Using UV (Recommended / UV 사용 권장)
uv run python scripts/run_webpage_finder.py "<firm_name>"

# Using standard Python (일반 파이썬 사용)
python scripts/run_webpage_finder.py "<firm_name>"
```

**Example / 예시:**
```bash
uv run python scripts/run_webpage_finder.py "네이버"
```

**Output format / 출력 형식:**
```text
============================================================
✓ Found firm webpage!
============================================================
URL: https://www.navercorp.com/
Confidence: high
Reasoning: The search results point to navercorp.com as the official company portal...
```

---

## 5. Geocoding & Map Data Generator / 지오코딩 및 지도 데이터 생성기

Converts address strings in a CSV list into exact latitude and longitude coordinates. It generates the `src/firm_analyzer/web/static/js/firms_data.js` file used to render markers on the interactive map page.

CSV 목록에 포함된 한글 주소 문자열을 위경도 좌표로 변환합니다. 웹페이지 대화형 지도상에 마커를 시각화하기 위한 `src/firm_analyzer/web/static/js/firms_data.js` 파일을 작성합니다.

### Geocoding Strategy / 지오코딩 계층 구조:
1. **Kakao Maps API (Best/가장 정확)**: Requires `KAKAO_REST_API_KEY`. Perfect for both Road Name (도로명) and Lot Number (지번) addresses.
2. **Nominatim OSM (Fallback/보완책)**: Free fallback. Requires `geopy` library.
3. **Regional Center Fallback (Final Fallback/기본 좌표)**: Hardcoded coordinates representing the district (구) or city with small randomized offsets.

### Run Instructions / 실행 방법

```bash
# Using UV (Recommended / UV 사용 권장)
uv run python scripts/run_geocoding.py [options]

# Using standard Python (일반 파이썬 사용)
python scripts/run_geocoding.py [options]
```

**Common Examples / 자주 쓰는 예시:**
```bash
# 1. Run with auto-detection (Kakao key set in .env will be auto-used)
# (자동 감지 모드로 실행: .env에 Kakao 키가 있으면 자동으로 사용됨)
uv run python scripts/run_geocoding.py

# 2. Force API usage (API 사용 강제)
uv run python scripts/run_geocoding.py --use-api

# 3. Disable API calls and use fallback coordinates only (인터넷 API 비활성화 및 기본 지역 좌표만 사용)
uv run python scripts/run_geocoding.py --no-api
```

**Arguments / 옵션:**
- `--use-api`: Force geocoding using external APIs (Kakao/Nominatim)
- `--no-api`: Disable API requests and map directly to static regional fallback coordinates
- *Alternatively, set environment variable `USE_GEOCODING_API=1` or `0`.*

---

## 6. Supabase Sync Engine / Supabase 동기화 엔진

Uploads and synchronizes local CSV data along with generated summaries (`summary.md`, `raw_search.json`, `webpage.json`) to a central Supabase PostgreSQL database. It handles conflicts on the unique company name via upsert operations.

로컬 CSV 데이터와 기존에 생성된 요약 정보(`summary.md`, `raw_search.json`, `webpage.json`)를 취합하여 중앙 Supabase PostgreSQL 데이터베이스에 동기화(업로드)합니다. 고유한 회사 이름 기준의 Upsert 동작을 통해 데이터 충돌 및 중복을 방지합니다.

*Requires Supabase environment variables / Supabase 환경변수 필요:*
```env
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_or_service_key
```

### Run Instructions / 실행 방법

```bash
# Using UV (Recommended / UV 사용 권장)
uv run python scripts/run_supabase_sync.py

# Using standard Python (일반 파이썬 사용)
python scripts/run_supabase_sync.py
```

---

## 7. Web Application Engine / 웹 애플리케이션 서비스

Runs the local Flask web server, which serves the React interface (build it once with `cd frontend && npm ci && npm run build`), the JSON API, and the map. The interface manages the yearly 인원배정 list, edits `config.yml`, runs the pipeline as background jobs, and searches the summaries.

로컬 Flask 웹 서버를 실행합니다. React 화면(`cd frontend && npm ci && npm run build`로 한 번 빌드), JSON API, 지도를 제공합니다. 화면에서 연도별 인원배정 명단 관리, `config.yml` 편집, 파이프라인 백그라운드 실행, 요약 검색을 할 수 있습니다.

### Run Instructions / 실행 방법

```bash
# Using UV (Recommended / UV 사용 권장)
uv run python scripts/run_app.py

# Using standard Python (일반 파이썬 사용)
python scripts/run_app.py
```

- **Default URL**: http://localhost:8001
- **Available Views**:
  - `http://localhost:8001/` - Dashboard / 대시보드
  - `http://localhost:8001/rosters` - 전문연 명단 관리 (import, compare, activate)
  - `http://localhost:8001/pipeline` - Pipeline jobs / 파이프라인 실행
  - `http://localhost:8001/summary` - Summary search and viewer / 요약 결과 보기
  - `http://localhost:8001/config` - Settings / 설정 변경
  - `http://localhost:8001/map` - Interactive map / 대화형 지도
