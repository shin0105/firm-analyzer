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
