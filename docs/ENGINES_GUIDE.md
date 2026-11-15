# Engines Guide / 엔진 사용 가이드

This document provides a comprehensive overview of the different processing and execution engines within the **Firm Analyzer** system. It details their purpose, how they fit into the workflow, and instructions on how to run them via the command line in both **English** and **Korean**.

본 문서는 **Firm Analyzer** 시스템의 다양한 처리 및 실행 엔진에 대한 종합적인 개요를 제공합니다. 각 엔진의 목적, 워크플로우에서의 역할, 그리고 명령행(CLI)에서 실행하는 방법을 **영어**와 **한국어**로 작성하였습니다.

The yearly list (`firm-roster`), segmentation backfill (`firm-segment`), the CSV export (`firm-export`) and the static site (`firm-export-site`) are not covered here; see the [main README](../README.md).
연도별 명단 관리(`firm-roster`), 세분류 보충(`firm-segment`), CSV 내보내기(`firm-export`), 정적 사이트(`firm-export-site`)는 이 문서에서 다루지 않습니다. [README](../README.md)를 참고하세요.

Every command below is an installed entry point (`uv run firm-...`). From a checkout, each one also runs as `uv run python scripts/run_<name>.py`.
아래 명령은 모두 설치된 엔트리 포인트(`uv run firm-...`)입니다. 체크아웃에서는 `uv run python scripts/run_<name>.py`로도 실행할 수 있습니다.

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
1. **Rule-Based Extraction** (using `pdfplumber` to extract tables programmatically; no API key).
2. **LLM-Based Extraction** (using the selected LLM provider: OpenAI, Claude, Gemini or GitHub Models). Claude and Gemini read the PDF itself, page images included. OpenAI and GitHub Models only get the text that `pdfplumber` extracts, so they cannot read a scanned PDF.

PDF 파싱 엔진은 공식 정부 문서 또는 기업 PDF 목록(예: 전문연구요원 인원배정 현황 PDF)을 구조화된 CSV 파일로 변환합니다. 두 가지 방식을 지원합니다:
1. **규칙 기반 추출** (`pdfplumber`를 사용하여 표 구조를 프로그래밍 방식으로 추출. API 키 불필요).
2. **LLM 기반 추출** (선택한 LLM 제공자 사용: OpenAI, Claude, Gemini, GitHub Models). Claude와 Gemini는 PDF 자체(페이지 이미지 포함)를 읽습니다. OpenAI와 GitHub Models는 `pdfplumber`가 추출한 텍스트만 받으므로 스캔한 PDF는 읽을 수 없습니다.

To import a yearly 인원배정 list for the pipeline, use `uv run firm-roster import <pdf> --year <year>` (or the **전문연 명단 관리** page), which wraps both parsers.
파이프라인용 연도별 명단은 두 파서를 감싼 `firm-roster import`(또는 **전문연 명단 관리** 화면)로 가져오세요.

### Run Instructions / 실행 방법

#### A. Rule-Based Parser (규칙 기반 파서)
This command parses tables using programmatic layout rules and supports Korean city extraction and column renaming.
이 명령은 표 레이아웃 규칙을 통해 분석하며, 주소에서 한국 도시명 추출 및 열 이름 변경을 지원합니다.

```bash
# Installed command (Recommended / 권장)
uv run firm-parse-pdf --pdf <file.pdf> [options]

# Wrapper script (래퍼 스크립트)
uv run python scripts/run_pdf_parser_rule.py --pdf <file.pdf> [options]
```

**Common Examples / 자주 쓰는 예시:**
```bash
# 1. Parse a 인원배정 PDF with the default columns (기본 열로 파싱)
uv run firm-parse-pdf --pdf data/2026_전문연구요원_인원배정.pdf

# 2. Extract city name from address column (주소 열에서 도시명 자동 추출 추가)
uv run firm-parse-pdf --pdf data/2026_전문연구요원_인원배정.pdf --extract-city-from-location

# 3. Parse custom PDF with custom columns (사용자 정의 PDF 및 열 지정)
uv run firm-parse-pdf \
  --pdf data/my_firms.pdf \
  --output data/my_firms.csv \
  --columns "번호" "회사명" "소재지" "관할청"

# 4. Map and rename columns during parsing (파싱 중 열 이름 변경 매핑)
uv run firm-parse-pdf \
  --pdf data/my_firms.pdf \
  --columns "번호:Number" "회사명:Company Name" "소재지:Location"
```

**Arguments / 옵션:**
- `-p`, `--pdf`: Input PDF path (required)
- `-o`, `--output`: Output CSV path (Default: `<pdf name>_parsed.csv` next to the PDF)
- `-c`, `--columns`: Space-separated column list or mapping format `source:target` (Default: `연번 업종구분 업체명 소재지 배정인원 관할청`)
- `--extract-city-from-location`: Extracts city division (e.g. `서울특별시`, `수원시`) into a new `도시` column
- `--min-columns`: Minimum non-empty fields to identify a row as valid (Default: `3`)

---

#### B. LLM-Based Parser (LLM 기반 파서)
The web UI uses this engine when you choose **AI로 추출** on the **전문연 명단 관리** page (`firm-roster import --method llm` does the same). It also has its own command, and can be called from Python.
**전문연 명단 관리** 화면에서 **AI로 추출**을 선택하면 이 엔진이 사용됩니다(`firm-roster import --method llm`도 동일). 별도 명령으로 실행하거나 파이썬에서 호출할 수도 있습니다.

*Requires API Key in `.env` / `.env` 파일에 API 키 설정 필요:*
```env
LLM_PROVIDER=gemini          # openai | claude | gemini | github
GEMINI_API_KEY=your_gemini_key
# or the key of the provider you chose / 또는 선택한 제공자의 키:
# OPENAI_API_KEY, ANTHROPIC_API_KEY, GITHUB_TOKEN
```

```bash
# Installed command (Recommended / 권장)
uv run firm-parse-pdf-llm <file.pdf> [options]

# Wrapper script (래퍼 스크립트)
uv run python scripts/run_pdf_parser_llm.py <file.pdf> [options]
```

**Example / 예시:**
```bash
# Writes data/my_document_parsed.csv (data/my_document_parsed.csv 생성)
uv run firm-parse-pdf-llm data/my_document.pdf --provider claude
```

**Arguments / 옵션:**
- `pdf`: Input PDF path (required). The CSV is written next to it as `<pdf name>_parsed.csv`, with `업체명` and `소재지` first, then whatever other columns the model found.
- `--provider`: `openai`, `claude`, `gemini` or `github` (Default: `LLM_PROVIDER`, then `app.llm_provider` in `config.yml`)
- `--model`: Override the provider's parser model for this run
- `--pages-per-chunk`: Pages sent per request (Default: `PDF_PAGES_PER_CHUNK`, or `6`). Lower it if the model runs out of output tokens on dense tables.

**Usage inside Python / 파이썬 내부 사용 예시:**
```python
from firm_analyzer.core.pdf_parser_llm import extract_pdf_rows, parse_pdf_to_csv

# Writes data/my_document_parsed.csv and returns its file name, "my_document_parsed.csv"
csv_name = parse_pdf_to_csv("data/my_document.pdf", provider="gemini")

# Or get the rows as a list of dicts without writing a file (파일 없이 행 목록만 받기)
rows = extract_pdf_rows("data/my_document.pdf", provider="claude")
```

---

## 2. Filtering Engine / 필터링 엔진

Filters the active 인원배정 list (or another CSV) using the location filter in `config.yml`, or values given on the command line. It ensures you only process companies in target regions, reducing API costs in subsequent search steps.

활성 인원배정 명단(또는 다른 CSV)을 `config.yml`의 위치 필터나 명령행에서 지정한 값으로 필터링합니다. 타겟 지역의 기업들만 선별함으로써 후속 웹 검색 단계의 API 비용을 절감합니다.

### Run Instructions / 실행 방법

```bash
# Installed command (Recommended / 권장)
uv run firm-filter [options]

# Wrapper script (래퍼 스크립트)
uv run python scripts/run_filter.py [options]
```

**Common Examples / 자주 쓰는 예시:**
```bash
# 1. Filter using settings from config.yml (config.yml 설정대로 필터링)
uv run firm-filter

# 2. Override location filter via command line (명령행으로 특정 지역 지정 필터링)
uv run firm-filter --locations 서울 경기 --filter-type contains

# 3. Specify custom input and output files; writes data/filtered.csv
#    (입출력 파일명 직접 지정, data/filtered.csv 생성)
uv run firm-filter -i data/custom_companies.csv -o filtered.csv
```

**Arguments / 옵션:**
- `-i`, `--input`: Input CSV file path (Default: the active 인원배정 list, see `uv run firm-roster list`)
- `-o`, `--output`: Output CSV file path (Default: `data/filtered_firms.csv`, the file summarize reads by default). A relative path is placed under `data/`, so `-o filtered.csv` writes `data/filtered.csv`. / 상대 경로는 `data/` 아래에 저장됩니다.
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
# or ANTHROPIC_API_KEY / GEMINI_API_KEY / GITHUB_TOKEN, matching LLM_PROVIDER
```

### Run Instructions / 실행 방법

```bash
# Installed command (Recommended / 권장)
uv run firm-summarize [options]

# Wrapper script (래퍼 스크립트)
uv run python scripts/run_summarize.py [options]
```

**Common Examples / 자주 쓰는 예시:**
```bash
# 1. Test search query structure without making API calls (API 호출 없이 쿼리 구조 확인 - 드라이런)
uv run firm-summarize --dry-run

# 2. Run summarization for only the first 5 firms (처음 5개 기업만 요약 생성 진행)
uv run firm-summarize --limit 5

# 3. Process a different input file (다른 입력 파일로 실행)
uv run firm-summarize --input data/my_firms.csv

# 4. Use another provider for this run (이번 실행만 다른 제공자 사용)
uv run firm-summarize --provider claude --limit 5
```

**Arguments / 옵션:**
- `-i`, `--input`: Input filtered CSV file (Default: `data/filtered_firms.csv`, the filter's output)
- `-o`, `--output-dir`: Output directory path (Default: `output.directory` in `config.yml`, `firm_results/`)
- `--dry-run`: Validates input and logs queries without performing live web search or LLM generation
- `--limit`: Limits the number of firms processed in a single run (useful for testing and budget control)
- `--provider`: `openai`, `claude`, `gemini` or `github` (Default: `LLM_PROVIDER`, then `app.llm_provider` in `config.yml`)
- `--model`: Override the provider's model for this run
- `--no-segmentation`: Skip the multi-axis taxonomy classification (see [segmentation.md](segmentation.md))

---

## 4. Firm Webpage Finder / 회사 웹페이지 검색기

Performs a focused search using Tavily to find a company's official website URL, then gives the candidates' titles and snippets to an LLM, which picks the most likely official site and rates its confidence.

Tavily 검색을 활용해 기업의 공식 웹사이트 후보를 찾고, 후보들의 제목과 요약문을 LLM에 전달해 공식 웹사이트를 고르고 신뢰도를 매깁니다.

*Requires / 필수 API 키:* `TAVILY_API_KEY` and the key of the selected LLM provider

This command picks the provider from `--provider`, then `LLM_PROVIDER`, then `openai`; it does not read `app.llm_provider` in `config.yml`.
이 명령은 `--provider`, `LLM_PROVIDER`, `openai` 순으로 제공자를 고르며, `config.yml`의 `app.llm_provider`는 읽지 않습니다.

### Run Instructions / 실행 방법

```bash
# Installed command (Recommended / 권장)
uv run firm-find-webpage "<firm_name>" [--provider claude]

# Wrapper script (래퍼 스크립트)
uv run python scripts/run_webpage_finder.py "<firm_name>"
```

**Example / 예시:**
```bash
uv run firm-find-webpage "네이버"
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

Converts the addresses in the active 인원배정 list into latitude and longitude coordinates. It generates the `src/firm_analyzer/web/static/js/firms_data.js` file used to render markers on the interactive map page. Details: [GEOCODING.md](GEOCODING.md).

활성 인원배정 명단의 주소를 위경도 좌표로 변환합니다. 웹페이지 대화형 지도상에 마커를 시각화하기 위한 `src/firm_analyzer/web/static/js/firms_data.js` 파일을 작성합니다. 자세한 내용: [GEOCODING.md](GEOCODING.md).

### Geocoding Strategy / 지오코딩 계층 구조:
1. **Kakao Maps API (Best/가장 정확)**: Requires `KAKAO_REST_API_KEY`. Perfect for both Road Name (도로명) and Lot Number (지번) addresses.
2. **Nominatim OSM (Fallback/보완책)**: Free fallback. Requires `geopy` library.
3. **Regional Center Fallback (Final Fallback/기본 좌표)**: Hardcoded coordinates representing the district (구) or city with small randomized offsets.

> [!NOTE]
> `firm-geocode` does not read `.env`. Pass it with `uv run --env-file .env firm-geocode`, or `export KAKAO_REST_API_KEY=...` first.
> `firm-geocode`는 `.env`를 읽지 않습니다. `uv run --env-file .env firm-geocode`로 실행하거나 먼저 `export KAKAO_REST_API_KEY=...`를 실행하세요.

### Run Instructions / 실행 방법

```bash
# Installed command (Recommended / 권장)
uv run --env-file .env firm-geocode [options]

# Wrapper script (래퍼 스크립트)
uv run --env-file .env python scripts/run_geocoding.py [options]
```

**Common Examples / 자주 쓰는 예시:**
```bash
# 1. Auto-detection: with KAKAO_REST_API_KEY in the environment, the APIs are used;
#    without it, the command asks whether to use Nominatim (default: no)
#    (자동 감지: 환경에 KAKAO_REST_API_KEY가 있으면 API 사용, 없으면 Nominatim 사용 여부를 물어봄. 기본값은 사용 안 함)
uv run --env-file .env firm-geocode

# 2. Force API usage (API 사용 강제. Kakao 키가 없으면 Nominatim만 사용)
uv run --env-file .env firm-geocode --use-api

# 3. Disable API calls and use fallback coordinates only (인터넷 API 비활성화 및 기본 지역 좌표만 사용)
uv run firm-geocode --no-api
```

**Arguments / 옵션:**
- `--use-api`: Use the external APIs: Kakao if the key is set, then Nominatim
- `--no-api`: Disable API requests. Addresses already in `data/geocode_cache.json` keep their cached coordinates; the rest get regional fallback coordinates.
- *Alternatively, `USE_GEOCODING_API=1` (or `true`/`yes`) acts like `--use-api` when no flag is given. Any other value, including `0`, is ignored: use `--no-api` to turn the APIs off.*
- *또는 플래그 없이 `USE_GEOCODING_API=1`(또는 `true`/`yes`)을 설정하면 `--use-api`와 같습니다. `0` 등 다른 값은 무시되므로 API를 끄려면 `--no-api`를 사용하세요.*

The map page also needs `KAKAO_JS_API_KEY`, a different Kakao key that is sent to the browser. See [KOREAN_MAPS_SETUP.md](KOREAN_MAPS_SETUP.md).
지도 화면에는 브라우저로 전달되는 별도의 키인 `KAKAO_JS_API_KEY`도 필요합니다. [KOREAN_MAPS_SETUP.md](KOREAN_MAPS_SETUP.md)를 참고하세요.

---

## 6. Supabase Sync Engine / Supabase 동기화 엔진

Uploads the active 인원배정 list, joined with each firm's result folder (`summary.md`, `webpage.json`), to the `firms` table of a Supabase PostgreSQL database. `raw_search.json` (scraped pages) is uploaded only with `--include-raw-search`. It handles conflicts on the unique company name via upsert operations. Setup: [SUPABASE_SETUP.md](SUPABASE_SETUP.md).

활성 인원배정 명단과 각 기업의 결과 폴더(`summary.md`, `webpage.json`)를 합쳐 Supabase PostgreSQL 데이터베이스의 `firms` 테이블에 업로드합니다. `raw_search.json`(수집한 웹페이지)은 `--include-raw-search`를 지정할 때만 업로드됩니다. 고유한 회사 이름 기준의 Upsert 동작을 통해 데이터 충돌 및 중복을 방지합니다. 설정 방법: [SUPABASE_SETUP.md](SUPABASE_SETUP.md).

*Requires Supabase environment variables / Supabase 환경변수 필요:*
```env
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_or_service_key
```

### Run Instructions / 실행 방법

```bash
# Installed command (Recommended / 권장)
uv run firm-supabase-sync

# Also upload raw_search.json, only into a table that is not publicly readable
# (raw_search.json도 업로드. 공개 읽기가 불가능한 테이블에만 사용)
uv run firm-supabase-sync --include-raw-search

# Wrapper script (래퍼 스크립트)
uv run python scripts/run_supabase_sync.py
```

---

## 7. Web Application Engine / 웹 애플리케이션 서비스

Runs the local Flask web server, which serves the React interface (build it once with `cd frontend && npm ci && npm run build`), the JSON API, and the map. The interface manages the yearly 인원배정 list, edits `config.yml`, runs the pipeline as background jobs, and searches the summaries.

로컬 Flask 웹 서버를 실행합니다. React 화면(`cd frontend && npm ci && npm run build`로 한 번 빌드), JSON API, 지도를 제공합니다. 화면에서 연도별 인원배정 명단 관리, `config.yml` 편집, 파이프라인 백그라운드 실행, 요약 검색을 할 수 있습니다.

### Run Instructions / 실행 방법

```bash
# Installed command (Recommended / 권장)
uv run firm-app

# Wrapper script (래퍼 스크립트)
uv run python scripts/run_app.py
```

- **Default URL**: http://localhost:8001
- **Available Views**:
  - `http://localhost:8001/` - Overview / 개요
  - `http://localhost:8001/rosters` - 전문연 명단 관리 (import, compare, activate)
  - `http://localhost:8001/pipeline` - Pipeline jobs / 파이프라인 실행
  - `http://localhost:8001/summary` - Summary search and viewer / 업체 요약
  - `http://localhost:8001/config` - Settings / 설정 변경
  - `http://localhost:8001/map` - Interactive map / 대화형 지도
