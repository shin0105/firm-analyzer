# Publishing the viewer on Vercel

**English** · [한국어](VERCEL_DEPLOY.ko.md)

The hosted site is a **read-only, static copy** of the viewer: dashboard, firm
search, summaries, map and CSV download. The pipeline, settings and 명단 pages
are left out, because they write files and start jobs that spend your API quota.
Keep running those locally with `uv run firm-app`.

There is no Flask on Vercel. `firm-export-site` saves what the API would answer
as files, and the frontend's static build searches them in the browser.

> [!TIP]
> See the result first: the project's own copy runs at
> **<https://firm-analyzer.vercel.app>**, deployed with exactly the steps below.

## Before you start

- The local app set up as in the [Quick start](../README.md#quick-start)
  (Python 3.12+, uv, Node.js 22+).
- Summaries in `firm_results/`, made by [the pipeline](../README.md#running-the-pipeline).
- A [Vercel](https://vercel.com/signup) account. The free Hobby plan is enough.
- Optional, for the map: an app in
  [Kakao Developers](https://developers.kakao.com/console/app) and its
  **JavaScript** key, set as `KAKAO_JS_API_KEY` in `.env`. (The REST key in
  [KOREAN_MAPS_SETUP.md](KOREAN_MAPS_SETUP.md) is only for geocoding and stays
  on your machine.)
- Optional, for [automatic deploys](#automatic-deploys): the
  [GitHub CLI](https://cli.github.com/), signed in with `gh auth login`.

## What becomes public

Everything in `frontend/static-site/`, which `firm-export-site` writes:

- every firm's `summary.md` (with the AI-generated notice) and segmentation,
- the CSV export (each row labelled AI-generated),
- the map page and its data (the public 병무청 list), with your Kakao **JavaScript** key.

Never included: `raw_search.json` (scraped pages), `webpage.json`, `.env`,
`config.yml` and every server-side key. The folder is git-ignored and leaves
your machine only by upload: to Vercel, and, with [automatic deploys](#automatic-deploys),
as the `static-site.tar.gz` file of the repository's `site-data` release, which
is public when the repository is.

> [!IMPORTANT]
> You are publishing AI-written text about real companies. Keep the notices,
> give companies a way to reach you, and remove a firm when asked
> ([Removing a firm](#removing-a-firm)). See the operator duties in
> [DISCLAIMER.md](../DISCLAIMER.md).

## One-time setup

1. **Restrict the Kakao key to your site.** In Kakao Developers
   (<https://developers.kakao.com/console/app>), open your app, go to
   **앱 → 플랫폼 키 → JavaScript 키 → JavaScript SDK 도메인** (formerly
   "사이트 도메인"), and add `https://<project>.vercel.app`, plus any custom
   domain. Enter the bare origin, with no path. Until then the map page shows
   the firm list and a "지도를 로드할 수 없습니다" message instead of the map.
   You learn the exact URL after the first deploy, so it is fine to come back
   to this step.
2. **Link the frontend folder to a Vercel project:**

   ```bash
   cd frontend
   npx vercel login
   npx vercel link
   npx vercel pull --yes --environment=production
   ```

   `vercel link` creates the project and writes `frontend/.vercel/` (git-ignored).
   [`frontend/vercel.json`](../frontend/vercel.json) sets the build command, the
   output folder and the routing, so the defaults it offers are fine. The
   project name becomes the URL: a project called `firm-analyzer` is served at
   `https://firm-analyzer.vercel.app` if that name is free. No environment
   variables are needed on Vercel.

## Each deploy

After summarizing new firms, or deleting a firm's folder from `firm_results/`,
snapshot the data and publish it. With [automatic deploys](#automatic-deploys)
set up, that is:

```bash
uv run firm-export-site
scripts/publish_site_data.sh     # uploads the snapshot and starts the Deploy workflow
```

Changes to the frontend or the map page need no command at all: merging them
into `main` deploys them. Without automatic deploys, build and upload by hand:

```bash
uv run firm-export-site
cd frontend
npx vercel build --prod
npx vercel deploy --prebuilt --prod
```

`firm-export-site` prints how many firms it wrote and warns if
`KAKAO_JS_API_KEY` is missing. `vercel build` builds on your machine and
`--prebuilt` uploads only the result. The last command prints the deployment
URL; the production URL now points to it.

To look at the static build locally first:

```bash
cd frontend && npm run build:static && npm run preview:static   # http://localhost:4173
```

To see what is live, run `npx vercel ls --prod` in `frontend/`.

## Automatic deploys

[`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml) deploys to
production on every push to `main` that touches `frontend/` or the map page's
script and styles (`src/firm_analyzer/web/static/`), and whenever it is started
by hand (**Actions → Deploy → Run workflow**, or `gh workflow run deploy.yml`).

The data is not in git, so the workflow downloads it: `static-site.tar.gz` on
the `site-data` release, which `scripts/publish_site_data.sh` replaces with your
latest `firm-export-site` snapshot. A release file can be replaced or deleted,
so a removal request takes effect everywhere; a committed snapshot would keep
every summary in the history for good. The workflow then builds with the Vercel
CLI exactly as the manual steps do, using the map page's script, styles and
roster from the commit being deployed.

### Set it up once

1. **Create a Vercel token** at <https://vercel.com/account/tokens> (scope: the
   team that owns the project). Treat it like a password.
2. **Add three repository secrets** (**Settings → Secrets and variables →
   Actions**), or with the GitHub CLI from the repository root:

   ```bash
   gh secret set VERCEL_TOKEN                     # paste the token when asked
   gh secret set VERCEL_ORG_ID --body "$(node -p "require('./frontend/.vercel/project.json').orgId")"
   gh secret set VERCEL_PROJECT_ID --body "$(node -p "require('./frontend/.vercel/project.json').projectId")"
   ```

   The two ids come from `frontend/.vercel/project.json`, which `vercel link`
   wrote.
3. **Upload the first snapshot** (needs `gh auth login`):

   ```bash
   uv run firm-export-site
   scripts/publish_site_data.sh --no-deploy
   ```

   Leave out `--no-deploy` once the workflow file is on `main`; the script then
   starts a deploy itself.

The workflow fails with a clear message if a secret or the release file is
missing. It never runs the pipeline and holds no AI or search keys.

### What still needs a new snapshot

The map page's HTML, with your Kakao JavaScript key, is rendered by
`firm-export-site`. After changing `src/firm_analyzer/web/templates/` or the
key, run `uv run firm-export-site && scripts/publish_site_data.sh`.

### Why Vercel's own git builds stay off

A build on Vercel's servers starts from the repository, which has no
`firm_results/`, so it would publish an empty viewer. That is why `vercel.json`
keeps `git.deploymentEnabled: false` and why there is no "Deploy with Vercel"
button. The workflow above builds on GitHub with the data added, and uploads the
result the same way you would.

`npm run build:static` writes an ordinary static site to `frontend/dist/`, so
another static host (Netlify, Cloudflare Pages, GitHub Pages) works too. Copy the
rewrite in `vercel.json`: paths outside `assets/`, `data/`, `map/` and `static/`
should serve `index.html`.

## Removing a firm

For a correction or removal request (see the 이용 안내 page), delete the firm's
folder from `firm_results/` and deploy again (`uv run firm-export-site`, then
`scripts/publish_site_data.sh`, which also replaces the release file). Earlier
deployments keep their own URLs, so to remove the old text everywhere, delete those deployments in the
Vercel dashboard (**Deployments → ⋯ → Delete**) or with
`npx vercel remove <deployment-url>`.

## Differences from the local app

- Search matches a firm's name, address and summary prose. The local server
  also matches the summary's header, source list and AI notice, so a term like
  "AI" can find a few more firms there.
- The data is as of the last `firm-export-site`. The dashboard's 새로고침
  reloads the same snapshot.
