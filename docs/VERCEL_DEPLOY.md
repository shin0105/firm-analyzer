# Publishing the viewer on Vercel

The hosted site is a **read-only, static copy** of the viewer: dashboard, firm
search, summaries, map and CSV download. The pipeline, settings and 명단 pages
are left out, because they write files and start jobs that spend your API quota.
Keep running those locally with `uv run firm-app`.

There is no Flask on Vercel. `firm-export-site` saves what the API would answer
as files, and the frontend's static build searches them in the browser.

## What becomes public

Everything in `frontend/static-site/`, which `firm-export-site` writes:

- every firm's `summary.md` (with the AI-generated notice) and segmentation,
- the CSV export (each row labelled AI-generated),
- the map page and its data (the public 병무청 list), with your Kakao **JavaScript** key.

Never included: `raw_search.json` (scraped pages), `webpage.json`, `.env`,
`config.yml` and every server-side key. The folder is git-ignored and is uploaded
from your machine only.

## One-time setup

1. Restrict the Kakao key to your site. In Kakao Developers, open your app,
   go to **플랫폼 → Web → 사이트 도메인**, and add `https://<project>.vercel.app`
   (plus any custom domain). Until then the map page shows the firm list and
   a "지도를 로드할 수 없습니다" message instead of the map.
2. Link the frontend folder to a Vercel project:

   ```bash
   cd frontend
   npx vercel link
   npx vercel pull --yes --environment=production
   ```

   `vercel link` creates the project and writes `frontend/.vercel/` (git-ignored).
   [`frontend/vercel.json`](../frontend/vercel.json) sets the build command, the
   output folder and the routing, so the defaults it offers are fine. No
   environment variables are needed on Vercel.

## Each deploy

After summarizing new firms, or deleting a firm's folder from `firm_results/`:

```bash
uv run firm-export-site
cd frontend
npx vercel build --prod
npx vercel deploy --prebuilt --prod
```

`vercel build` builds on your machine and `--prebuilt` uploads only the result.
A build on Vercel's servers would start from the GitHub repository, which has
no `firm_results/`, so `vercel.json` turns off deploys from git pushes
(`git.deploymentEnabled: false`).

To look at the static build locally first:

```bash
cd frontend && npm run build:static && npm run preview:static   # http://localhost:4173
```

## Removing a firm

For a correction or removal request (see the 이용 안내 page), delete the firm's
folder from `firm_results/` and deploy again. Earlier deployments keep their own
URLs, so to remove the old text everywhere, delete those deployments in the
Vercel dashboard (**Deployments → ⋯ → Delete**) or with
`npx vercel remove <deployment-url>`.

## Differences from the local app

- Search matches a firm's name, address and summary prose. The local server
  also matches the summary's header, source list and AI notice, so a term like
  "AI" can find a few more firms there.
- The data is as of the last `firm-export-site`. The dashboard's 새로고침
  reloads the same snapshot.
