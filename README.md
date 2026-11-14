# Firm Analyzer · 전문연구요원 지정업체 분석 도구

A tool for exploring the firms on the Military Manpower Administration's yearly
전문연구요원 인원배정 list: import the list, filter it by location, search the
web for each firm, and have an AI summarize and classify what it finds.

> [!WARNING]
> **AI 생성 콘텐츠 · 참고용** — 기업 요약과 분류는 공개 웹 검색 결과를 바탕으로 AI가
> 자동 생성한 참고 자료입니다. 사실과 다르거나 오래된 정보, 동명의 다른 기업 정보가 섞여
> 있을 수 있으며 해당 기업의 공식 입장이나 평가가 아닙니다. 중요한 결정 전에는 반드시 기업의
> 공식 채널과 병무청에서 직접 확인하세요.
>
> **AI-generated, for reference only** — firm summaries and classifications are
> written automatically by an AI model from public web search results. They can
> be wrong, outdated or mix up firms with similar names, and they are not
> statements by the companies. Verify anything important with official sources.
>
> See **[DISCLAIMER.md](DISCLAIMER.md)** for the full terms.

## How it works

```
 병무청 인원배정 PDF ──► 명단 (data/<year>_전문연구요원_인원배정.csv)
                              │  firm-roster import / 전문연 명단 관리 page
                              ▼
                        filter by location ──► data/filtered_firms.csv
                              │  firm-filter
                              ▼
               web search (Tavily) + AI summary & segmentation
                              │  firm-summarize
                              ▼
                firm_results/<category>/<firm>/summary.md …
                              │
                              ▼
          web UI: dashboard · search · map · CSV export
```

- **Yearly list updates.** Upload the new 인원배정 PDF (or a CSV) and the app
  extracts every row, checks the row count against the last 연번, shows which
  firms are new and which dropped off, and switches the pipeline to the new list.
- **Choose your AI.** OpenAI, Claude, Gemini or GitHub Models; you only need a
  key for the one you use.
- **Multi-axis segmentation.** Sector, technology verticals, business model,
  value-chain position and organisation profile, each with a confidence level
  and an evidence sentence. The taxonomy is data: [`taxonomy.yml`](taxonomy.yml),
  explained in [docs/segmentation.md](docs/segmentation.md).
- **Traceable output.** Every summary carries the AI-generated notice and lists
  the search results it was built from.
- **Background jobs.** Filter, summarize and segment run as subprocesses with a
  live log, progress bar and cancel button.

## Quick start

Requirements: Python 3.12+, [uv](https://docs.astral.sh/uv/), and Node.js 22+
for the web interface.

```bash
uv sync                          # Python dependencies
cp .env.example .env             # then add your keys (see below)
cd frontend && npm ci && npm run build && cd ..
uv run firm-app                  # http://localhost:8001
```

The minimum `.env` is a search key and the key for one AI provider:

```
TAVILY_API_KEY=...
LLM_PROVIDER=openai              # openai | claude | gemini | github
OPENAI_API_KEY=...               # or ANTHROPIC_API_KEY / GEMINI_API_KEY
```

`.env.example` documents every variable. `.env` and `config.yml` are
git-ignored; never commit them.

**Developing the frontend:** run `uv run firm-app` in one terminal and
`npm run dev` in `frontend/` in another, then open http://localhost:5173. The
dev server forwards `/api` to Flask, so both run on one origin.

**Security:** the server binds to `127.0.0.1`. The API has no authentication and
can start subprocesses that spend your API quota, so only expose it
(`FLASK_HOST`) on a network you trust.

## Updating the 전문연 list (명단 업데이트)

Each year the 병무청 publishes a new 「전문연구요원 인원배정 현황」 PDF.

**In the web UI:** open **전문연 명단 관리**, drop the PDF, check the year, and
press **가져오기**. You get:

- the new list saved as `data/<year>_전문연구요원_인원배정.csv` (the PDF is kept
  next to it as the source record),
- a warning if the number of rows does not match the last 연번, which means
  the table extraction missed or duplicated rows,
- a comparison with the previous list: firms added, firms removed, and how
  many stayed, each downloadable as CSV,
- the new list made the pipeline's input (untick the option to keep the old one).

Then run **필터 후 요약** on the 파이프라인 실행 page. Firms that were already
summarized are skipped, so only the new firms cost API calls.

PDF extraction defaults to table recognition (pdfplumber: free, a few seconds).
For a scanned PDF without a text layer, choose **AI로 추출**, which sends the
pages to the selected AI provider.

**From the command line:**

```bash
uv run firm-roster import ~/Downloads/2027_전문연구요원_인원배정.pdf --year 2027
uv run firm-roster list                    # * marks the active list
uv run firm-roster compare 2026_전문연구요원_인원배정.csv 2027_전문연구요원_인원배정.csv --out-dir data/diff
uv run firm-roster activate 2026_전문연구요원_인원배정.csv   # switch back
uv run firm-roster import list.csv --year 2027 --overwrite  # a CSV (UTF-8 or CP949)
uv run firm-roster import scan.pdf --year 2027 --method llm --provider gemini
```

The active list is `data.roster` in `config.yml`; when it is unset, the newest
`<year>_전문연구요원_인원배정.csv` in `data/` is used. Firms are matched across
years by name, ignoring legal-form markers such as (주)/㈜/주식회사 and spacing.
A firm whose lab was renamed shows up as one removal and one addition.

To refresh the map for the new list, regenerate its data with
`uv run firm-geocode` (see [docs/GEOCODING.md](docs/GEOCODING.md)).

## Running the pipeline

The **파이프라인 실행** page runs each stage as a background job. From the command
line:

```bash
uv run firm-filter                                  # active list -> data/filtered_firms.csv
uv run firm-filter --locations 서울 경기            # override config.yml's location filter
uv run firm-summarize --dry-run                     # show the search queries only
uv run firm-summarize --limit 10                    # search, summarize and segment 10 firms
uv run firm-summarize --provider claude --limit 10
uv run firm-segment --dry-run                       # backfill segmentation for older summaries
uv run firm-export                                  # every firm -> firm_results/firms_export.csv
```

A firm that fails (bad model output, a search error) is skipped and reported;
only a rate-limit or quota error stops the run. Re-running retries exactly the
failed firms.

Each firm gets a folder in `firm_results/<category>/<firm>/`:

| File | Contents |
|------|----------|
| `summary.md` | Header, AI notice, segmentation table, summary, 출처 (sources) |
| `segmentation.json` | The structured classification |
| `raw_search.json` | The search response the summary was built from (scraped page text; keep it private) |
| `webpage.json` | The firm's official site, when found |

## Publishing the viewer (Vercel)

The dashboard, firm search, summaries, map and CSV can be published as a static,
read-only site; the pipeline keeps running on your machine.

```bash
uv run firm-export-site                      # snapshot -> frontend/static-site/ (git-ignored)
cd frontend
npx vercel build --prod && npx vercel deploy --prebuilt --prod
```

Everything in the snapshot becomes public, but it never includes
`raw_search.json` or any server-side key. First-time setup, Kakao domains and
removing a firm: [docs/VERCEL_DEPLOY.md](docs/VERCEL_DEPLOY.md).

## Configuration

Settings live in `config.yml`, editable in the **설정 변경** page or by hand.
Start from the template, or let the app use its built-in defaults:

```bash
cp config.example.yml config.yml
```

| Section | What it controls |
|---------|------------------|
| `app.llm_provider`, `app.llm_models` | Which AI runs, and model overrides |
| `data.roster` | The active 인원배정 list (empty = newest year) |
| `filters.location` | Column, match type and values for the location filter |
| `categories` | Coarse buckets used for the output folders and dashboard |
| `search` | Tavily query template, depth, result count, extra context |
| `summary` | Language, focus areas, custom prompt, system prompt |
| `segmentation.enabled` | Classify against `taxonomy.yml` in the same call as the summary |

Custom prompts can change what a summary covers, but the content rules in
[`src/firm_analyzer/notice.py`](src/firm_analyzer/notice.py) (stick to the
sources, stay neutral, no unsupported negative claims, no personal data) are
always added to the system prompt.

## Commands

| Command | Purpose |
|---------|---------|
| `firm-app` | Web server (API, built frontend, map) |
| `firm-roster` | Import, list, compare and activate 인원배정 lists |
| `firm-filter` | Location filter over the active list |
| `firm-summarize` | Search, summarize and segment |
| `firm-segment` | Segment firms summarized before segmentation existed |
| `firm-export` | Rebuild one CSV from the result folders |
| `firm-export-site` | Snapshot the read-only viewer as static files for Vercel |
| `firm-geocode` | Regenerate the map data from the active list |
| `firm-parse-pdf` | Generic rule-based PDF table → CSV |
| `firm-parse-pdf-llm` | Generic AI PDF → CSV |
| `firm-supabase-sync` | Upload results to Supabase |
| `firm-find-webpage` | Find one firm's official website |

Every command also runs as `uv run python scripts/run_<name>.py` from a
checkout. More detail per engine: [docs/ENGINES_GUIDE.md](docs/ENGINES_GUIDE.md).

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/config` | GET, POST | Read or save `config.yml` |
| `/api/config/reset` | POST | Restore the default configuration |
| `/api/rosters` | GET | Lists in `data/` and the active one |
| `/api/rosters/import` | POST | Multipart `file` (PDF/CSV), `year`, `method` (`rule`/`llm`), `provider`, `activate`, `overwrite` |
| `/api/rosters/active` | POST | `{"name": "<csv>"}`: make a list the filter's input (409 while a job runs) |
| `/api/rosters/compare` | GET | `?base=&target=`: firms added, removed and kept |
| `/api/rosters/compare.csv` | GET | Same, one side (`part=added\|removed`) as CSV |
| `/api/rosters/<name>/download` | GET | Download a list |
| `/api/results/summary` | GET | Firm counts per category |
| `/api/results/<category_id>` | GET | Firms in a category with full summaries |
| `/api/firms` | GET | Search across categories: `q`, `category`, `sector`, `vertical`, `business_model`, `confidence`, `segmented` |
| `/api/firms/<category_id>/<firm_name>` | GET | One firm's `summary.md` and segmentation |
| `/api/taxonomy` | GET | The segmentation taxonomy |
| `/api/export.csv` | GET | Every firm as one CSV, each row labelled AI-generated |
| `/api/llm/providers` | GET | Providers, whether each has a key, and the active one |
| `/api/jobs` | GET, POST | List jobs, or start one: `{"kind": "filter"\|"summarize"\|"segment"\|"pipeline", "options": {...}}` |
| `/api/jobs/<id>?since=<n>` | GET | Status, progress and new log lines |
| `/api/jobs/<id>/cancel` | POST | Stop a running job |
| `/map` | GET | Map of the list's firms (Kakao Maps) |

One job runs at a time, because every stage writes the same files. Jobs live in
server memory and stop when the server exits.

## Data and privacy

- **Committed:** the public 병무청 인원배정 PDFs and their CSV conversions in
  `data/`, sample CSVs in `data/samples/`, and the map's coordinates
  (`firms_data.js`). These are public lists of designated organisations.
- **Never committed:** `firm_results/` (AI-written text about real companies and
  scraped web pages), `.env`, `config.yml`, caches. They are in `.gitignore`.
- **Supabase:** `firm-supabase-sync` uploads summaries with the AI notice and
  leaves out `raw_search.json` unless you pass `--include-raw-search`. The anon
  key is public by design, so enable Row Level Security before exposing the
  table. See [docs/SUPABASE_SETUP.md](docs/SUPABASE_SETUP.md).
- **Kakao:** `KAKAO_JS_API_KEY` is sent to the browser; restrict it to your
  domains in the Kakao console. `KAKAO_REST_API_KEY` stays on the server.
- **Static site:** `firm-export-site` writes summaries, segmentation, the CSV
  and the map to `frontend/static-site/` (git-ignored) for the Vercel deploy.
  Deploying it publishes them; scraped pages and keys other than the Kakao
  JavaScript key are never written.

## Project layout

```
src/firm_analyzer/
  core/        filter, summarize, roster (명단), segmentation, export, parsers, geocoding
  llm/         one interface over OpenAI, Claude, Gemini and GitHub Models
  web/         Flask API, job runner, map template and static files
  notice.py    the AI-generated notice and prompt content rules
frontend/      React + TypeScript web interface (Vite)
data/          인원배정 lists (PDF + CSV) and samples
docs/          guides for each engine, the data format, geocoding, Supabase
tests/         pytest suite
taxonomy.yml   the segmentation taxonomy
```

## Development

```bash
uv sync --extra dev && uv run pytest tests/ -q
cd frontend && npx tsc -b && npm run lint && npm run build
```

CI runs both, builds the wheel, and fails if a `.env` or a credential-shaped
string is committed.

## License

MIT, see [LICENSE](LICENSE). The software and its output come with no warranty;
see [DISCLAIMER.md](DISCLAIMER.md).
