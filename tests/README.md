# Test Files

Unit tests (no network, no API keys) plus a couple of manual scripts that do
hit live services.

## Unit tests

Run everything from the project root:

```bash
pytest
```

### test_llm_providers.py
Provider selection precedence (argument → `LLM_PROVIDER` → `config.yml` →
default), per-provider model resolution, and the tolerant JSON extraction that
handles each vendor's response style.

### test_segmentation.py
Taxonomy integrity (`taxonomy.yml`), prompt assembly, and the validation that
replaces model-invented labels with `unknown` instead of letting them into CSV
columns.

### test_pipeline.py
The filter → summarize hand-off (`data/filtered_firms.csv`), and summarize's
failure handling with stubbed search and LLM clients: a failed firm is skipped
and retried on the next run, a quota error stops the run without losing the
CSV rows already written, and an invented category id never becomes a
directory.

### test_resegment_export.py
`firm-segment` backfill (which firms it picks, where the 세분류 table goes,
`--relocate`, `--force`, failure and quota handling, `--dry-run`) and the
`firm-export` CSV rebuilt from the result folders.

### test_jobs.py
Background pipeline jobs: option validation (only fixed flags and checked ids
reach the command line), progress and summary parsing, log windowing, and the
runner against real `python -c` subprocesses — stdout streamed but stderr kept
out of the API, failure, cancel, timeout, and one job at a time. Also the
`/api/jobs` endpoints (including 409 on the legacy `/api/run/*` while a job
runs) and one real filter → summarize dry run in a throwaway project home.

### test_web_api.py
The Flask API through its test client: results and export endpoints, firm
search (`q`, each filter, 400 on unknown ids) and firm detail, including the
guard that only serves a firm folder directly inside its category (no "..",
separators or outward symlinks), plus the input checks on category ids,
summarize parameters and upload filenames.

### test_pdf_parser.py
Rule-based PDF parsing for firm data extraction.

### test_webpage_finder.py
Structure and response handling for the webpage finder.

## Manual scripts (spend real API calls)

### live_provider_check.py
One small JSON round trip per configured provider. Providers without a key are
skipped, not failed.

```bash
python tests/live_provider_check.py           # every configured provider
python tests/live_provider_check.py gemini    # just one
```

### test_kakao_geocoding.py
Kakao Maps geocoding against sample Korean addresses.

```bash
python tests/test_kakao_geocoding.py
```

## Environment variables

Copy `.env.example` to `.env` and fill in what you need. Only the key for the
provider you actually select is required:

```
TAVILY_API_KEY=...          # search
LLM_PROVIDER=openai         # openai | claude | gemini | github
OPENAI_API_KEY=...          # if LLM_PROVIDER=openai
ANTHROPIC_API_KEY=...       # if LLM_PROVIDER=claude
GEMINI_API_KEY=...          # if LLM_PROVIDER=gemini
KAKAO_REST_API_KEY=...      # geocoding only
```
