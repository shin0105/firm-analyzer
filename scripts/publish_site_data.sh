#!/usr/bin/env bash
# Publish new data: upload the static-site snapshot that Vercel's git builds
# download, then deploy it to production from this machine.
#
#   uv run firm-export-site                     # writes frontend/static-site/
#   scripts/publish_site_data.sh                # uploads it and deploys
#   scripts/publish_site_data.sh --no-deploy    # uploads only
#
# The snapshot becomes the `static-site.tar.gz` file of the `site-data` GitHub
# release, replacing the previous one. On a public repository that file is
# public too; it holds exactly what the hosted viewer serves.
#
# The deploy happens here, not through a git push: Vercel only builds commits
# that change frontend/ (frontend/vercel.json), and a data update changes no
# code. It runs only on a clean main that matches origin/main, so production
# always gets main's code. Needs the GitHub CLI (`gh auth login`) and, for the
# deploy, the Vercel CLI linked at the repository root (`npx vercel link`).
set -euo pipefail

cd "$(dirname "$0")/.."
SNAPSHOT=frontend/static-site
TAG=site-data
ASSET=static-site.tar.gz

deploy=true
case "${1:-}" in
  --no-deploy) deploy=false ;;
  "") ;;
  *)
    echo "Usage: $0 [--no-deploy]" >&2
    exit 2
    ;;
esac

if [ ! -f "$SNAPSHOT/data/firms.json" ]; then
  echo "No snapshot in $SNAPSHOT/. Run \`uv run firm-export-site\` first." >&2
  exit 1
fi

# The patterns of the CI secret scan: server-side keys must never be uploaded.
# (The Kakao JavaScript key in map/index.html is meant to be public.)
if grep -rlE 'tvly-[A-Za-z0-9-]{10}|gh[pous]_[A-Za-z0-9]{30}|github_pat_[A-Za-z0-9_]{30}|eyJhbGciOi[A-Za-z0-9]|(^|[^A-Za-z0-9])sk-(ant-)?[A-Za-z0-9_-]{20}|AIza[0-9A-Za-z_-]{30}|sb_secret_[A-Za-z0-9_-]{10}|AKIA[0-9A-Z]{16}' "$SNAPSHOT"; then
  echo "A credential-shaped string is in the files above. Not uploading." >&2
  exit 1
fi

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
# COPYFILE_DISABLE keeps macOS tar from adding ._* metadata files.
COPYFILE_DISABLE=1 tar -czf "$work/$ASSET" -C "$SNAPSHOT" .
firms=$(find "$SNAPSHOT/data/firms" -name '*.json' | wc -l | tr -d ' ')

if ! gh release view "$TAG" >/dev/null 2>&1; then
  gh release create "$TAG" --title "Site data" --latest=false --notes \
"The data the hosted viewer is built from: \`frontend/static-site/\` as written by \`uv run firm-export-site\`, packed as $ASSET.

It is replaced on every \`scripts/publish_site_data.sh\` run, and Vercel downloads it when it builds from git. It contains AI-written summaries about real companies, the same as the live site. See docs/VERCEL_DEPLOY.md."
fi
gh release upload "$TAG" "$work/$ASSET" --clobber
echo "Uploaded $ASSET ($firms firms, $(du -h "$work/$ASSET" | cut -f1 | tr -d ' ')) to the $TAG release."

$deploy || exit 0

git fetch --quiet origin main
if [ "$(git rev-parse --abbrev-ref HEAD)" != main ] ||
   [ "$(git rev-parse HEAD)" != "$(git rev-parse origin/main)" ] ||
   [ -n "$(git status --porcelain -- frontend src/firm_analyzer/web/static)" ]; then
  echo "Not deploying: this checkout is not a clean main matching origin/main." >&2
  echo "The new snapshot is uploaded and the next frontend change merged into main will use it." >&2
  echo "To deploy it now: git switch main && git pull, then run $0 again." >&2
  exit 0
fi
if [ ! -f .vercel/project.json ]; then
  echo "Link the repository root to the Vercel project once (npx vercel link), then run $0 again." >&2
  exit 1
fi

npx vercel pull --yes --environment=production
npx vercel build --prod
npx vercel deploy --prebuilt --prod
