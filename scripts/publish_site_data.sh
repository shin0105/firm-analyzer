#!/usr/bin/env bash
# Upload the static-site snapshot that the Deploy workflow builds from, then
# start a production deploy.
#
#   uv run firm-export-site                     # writes frontend/static-site/
#   scripts/publish_site_data.sh                # uploads it and deploys
#   scripts/publish_site_data.sh --no-deploy    # uploads only
#
# The snapshot becomes the `static-site.tar.gz` file of the `site-data` GitHub
# release, replacing the previous one. On a public repository that file is
# public too; it holds exactly what the hosted viewer serves. Needs the GitHub
# CLI, signed in (`gh auth login`).
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

It is replaced on every \`scripts/publish_site_data.sh\` run, and the Deploy workflow downloads it. It contains AI-written summaries about real companies, the same as the live site. See docs/VERCEL_DEPLOY.md."
fi
gh release upload "$TAG" "$work/$ASSET" --clobber
echo "Uploaded $ASSET ($firms firms, $(du -h "$work/$ASSET" | cut -f1 | tr -d ' ')) to the $TAG release."

if $deploy; then
  gh workflow run deploy.yml --ref main
  echo "Started the Deploy workflow on main. Follow it with: gh run watch"
fi
