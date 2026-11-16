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
- The [GitHub CLI](https://cli.github.com/), signed in with `gh auth login`, to
  upload the data snapshot.

## What becomes public

Everything in `frontend/static-site/`, which `firm-export-site` writes:

- every firm's `summary.md` (with the AI-generated notice) and segmentation,
- the CSV export (each row labelled AI-generated),
- the map page and its data (the public 병무청 list), with your Kakao **JavaScript** key.

Never included: `raw_search.json` (scraped pages), `webpage.json`, `.env`,
`config.yml` and every server-side key. The folder is git-ignored and leaves
your machine only by upload: as the `static-site.tar.gz` file of the
repository's `site-data` release, which is public when the repository is and
which Vercel downloads at build time ([Automatic deploys](#automatic-deploys)),
and as the deployments `scripts/publish_site_data.sh` uploads.

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
2. **Create the Vercel project from the repository.** In Vercel, **Add New →
   Project** and import your GitHub repository, or, for a project made with the
   CLI, **Settings → Git → Connect Git Repository**. Then, in **Settings → Build
   and Deployment**:
   - **Root Directory:** `frontend`. Keep **Include files outside the root
     directory in the Build Step** on: the build takes the map page's script and
     styles from `src/`.
   - Nothing else. [`frontend/vercel.json`](../frontend/vercel.json) sets the
     framework, build command, output folder, routing and the ignore step below.
     No environment variables are needed.

   The project name becomes the URL: a project called `firm-analyzer` is served
   at `https://firm-analyzer.vercel.app` if that name is free.
3. **Link the Vercel CLI at the repository root**, for deploying data from your
   machine. With Root Directory set to `frontend`, the CLI runs from the root:

   ```bash
   npx vercel login
   npx vercel link
   npx vercel pull --yes --environment=production
   ```

   This writes `.vercel/` (git-ignored). An older `frontend/.vercel/` can be
   deleted.
4. **Publish the first snapshot** (needs `gh auth login`, on an up-to-date
   `main`):

   ```bash
   uv run firm-export-site
   scripts/publish_site_data.sh
   ```

## Each deploy

- **Code:** a push to `main` that changes something in `frontend/` deploys to
  production; on any other branch, and so on every pull request, it makes a
  preview deployment that Vercel links in the PR. Pushes that change nothing in
  `frontend/` (Python, docs, the map page's code in `src/`) do not build. They
  go out with the next frontend deploy, or right away with
  `scripts/publish_site_data.sh` on `main`.
- **Data:** after summarizing new firms, or deleting a firm's folder from
  `firm_results/`:

  ```bash
  uv run firm-export-site
  scripts/publish_site_data.sh
  ```

  The script uploads the snapshot for later git builds, then builds and deploys
  it from your machine. It only deploys from a clean `main` that matches
  `origin/main`, so production always runs `main`'s code; elsewhere it uploads
  and tells you how to deploy. `--no-deploy` uploads only. Changing the map
  page's template (`src/firm_analyzer/web/templates/`) or the Kakao key also
  needs this, since `firm-export-site` renders that HTML.

`firm-export-site` prints how many firms it wrote and warns if
`KAKAO_JS_API_KEY` is missing.

To look at the static build locally first:

```bash
cd frontend && npm run build:static && npm run preview:static   # http://localhost:4173
```

To deploy by hand, run from the repository root:

```bash
npx vercel build --prod
npx vercel deploy --prebuilt --prod
```

To see what is live, run `npx vercel ls --prod`.

## Automatic deploys

**What triggers a build.** `frontend/vercel.json` has an ignore command,
`git diff --quiet "${VERCEL_GIT_PREVIOUS_SHA:-HEAD^}" HEAD -- .`, which Vercel
runs in the Root Directory before each git build. It compares the commit with
the last successful deployment of that branch (or with the previous commit on a
branch's first deploy) and skips the build when nothing in `frontend/` changed.
If the comparison cannot run, the build goes ahead. Vercel applies this step to
deploy hooks too, which is why data is deployed from your machine instead of
through a hook.

**Where the data comes from.** A build on Vercel's servers starts from the
repository, and the data is never committed: `firm_results/` and
`frontend/static-site/` hold AI-written text about real companies (the CI fails
if either is tracked). So the data travels separately, as `static-site.tar.gz`
on the repository's `site-data` release. `scripts/publish_site_data.sh` packs
your latest snapshot, refuses to upload anything that looks like a server-side
key, and replaces the previous file. The last step of `npm run build:static`
([`frontend/scripts/copy-static-site.mjs`](../frontend/scripts/copy-static-site.mjs))
finds no local snapshot on Vercel, downloads that file from the repository being
built (`VERCEL_GIT_REPO_OWNER`, `VERCEL_GIT_REPO_SLUG`) and copies it into the
site, with the map page's script, styles and roster from the commit itself.
`SITE_DATA_URL` overrides the download. A fork needs its own `site-data`
release.

A release file, unlike a commit, can be replaced or deleted, so a removal
request takes effect everywhere. The build holds no AI, search or GitHub keys
and never runs the pipeline.

`npm run build:static` writes an ordinary static site to `frontend/dist/`, so
another static host (Netlify, Cloudflare Pages, GitHub Pages) works too. Copy the
rewrite in `vercel.json`: paths outside `assets/`, `data/`, `map/` and `static/`
should serve `index.html`.

## Removing a firm

For a correction or removal request (see the 이용 안내 page), delete the firm's
folder from `firm_results/` and deploy again: `uv run firm-export-site`, then
`scripts/publish_site_data.sh`, which also replaces the release file. Earlier
deployments, previews included, keep their own URLs, so to remove the old text
everywhere, delete them in the Vercel dashboard (**Deployments → ⋯ → Delete**)
or with `npx vercel remove <deployment-url>`.

## Differences from the local app

- Search matches a firm's name, address and summary prose. The local server
  also matches the summary's header, source list and AI notice, so a term like
  "AI" can find a few more firms there.
- The data is as of the last `firm-export-site`. The dashboard's 새로고침
  reloads the same snapshot.
