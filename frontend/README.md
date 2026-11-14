# Firm Analyzer frontend

React + TypeScript (Vite) interface for the Flask API in `src/firm_analyzer/web`.

| Page | Route | What it does |
|------|-------|--------------|
| 대시보드 | `/` | Firm counts per category, CSV export |
| 전문연 명단 관리 | `/rosters` | Import a new 인원배정 list, compare lists, pick the active one |
| 파이프라인 실행 | `/pipeline` | Run filter, summarize and segment as background jobs |
| 인원배정 지도 | `/firms` | The map of listed firms (embeds Flask's `/map`) |
| 요약 결과 보기 | `/summary` | Search and read firm summaries |
| 설정 변경 | `/config` | Edit `config.yml` |
| 이용 안내 | `/about` | What the AI-generated content is, and the disclaimer |

Every view that shows AI-written content renders `components/AiNotice.tsx`.
Its wording mirrors `src/firm_analyzer/notice.py`; change both together.

## Running

```bash
npm ci
npm run dev      # http://localhost:5173, with /api proxied to Flask on :8001
npm run build    # dist/, which `uv run firm-app` serves at http://localhost:8001
npm run lint
npx tsc -b       # typecheck
```

Start the API first (`uv run firm-app` from the repository root). See
`.env.example` here for the two optional build variables.

## Static build (Vercel)

```bash
npm run build:static     # dist/ with the snapshot from `uv run firm-export-site`
npm run preview:static   # http://localhost:4173
```

`--mode static` sets `STATIC_SITE` (`src/lib/api.ts`): the pages marked
`needsServer` in `App.tsx` are hidden, and the remaining ones read the JSON
files in `data/` instead of calling `/api`. `vercel.json` here configures the
deploy. The full procedure is in
[docs/VERCEL_DEPLOY.md](../docs/VERCEL_DEPLOY.md); the live copy is
<https://firm-analyzer.vercel.app>.
