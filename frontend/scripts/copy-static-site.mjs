// Last step of `npm run build:static`: copy the snapshot written by
// `uv run firm-export-site` (data/, map/, static/) into the build.
//
// On your machine the snapshot is frontend/static-site/. A build on Vercel
// starts from the repository, which never holds it, so there the snapshot is
// downloaded first: static-site.tar.gz on the `site-data` release, which
// scripts/publish_site_data.sh uploads. SITE_DATA_URL overrides where it comes
// from.
//
// The map page's script, styles and roster are then taken from this checkout,
// so a change to them ships without a new snapshot.
import { execFileSync } from 'node:child_process';
import { cpSync, existsSync, mkdirSync, mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const source = fileURLToPath(new URL('../static-site/', import.meta.url));
const target = fileURLToPath(new URL('../dist/', import.meta.url));
const mapCode = fileURLToPath(new URL('../../src/firm_analyzer/web/static/', import.meta.url));

/** Where to download the snapshot from, or null to require a local one. */
function snapshotUrl() {
  if (process.env.SITE_DATA_URL) return process.env.SITE_DATA_URL;
  const owner = process.env.VERCEL_GIT_REPO_OWNER;
  const repo = process.env.VERCEL_GIT_REPO_SLUG;
  if (process.env.VERCEL && owner && repo) {
    return `https://github.com/${owner}/${repo}/releases/download/site-data/static-site.tar.gz`;
  }
  return null;
}

async function download(url) {
  console.log(`Downloading the site data from ${url}`);
  const response = await fetch(url, { redirect: 'follow' });
  if (!response.ok) {
    throw new Error(
      `HTTP ${response.status}. Upload a snapshot first: uv run firm-export-site, ` +
        'then scripts/publish_site_data.sh.',
    );
  }
  const archive = join(mkdtempSync(join(tmpdir(), 'site-data-')), 'static-site.tar.gz');
  writeFileSync(archive, Buffer.from(await response.arrayBuffer()));
  mkdirSync(source, { recursive: true });
  execFileSync('tar', ['-xzf', archive, '-C', source], { stdio: 'inherit' });
}

if (!existsSync(`${source}data/firms.json`)) {
  const url = snapshotUrl();
  if (!url) {
    console.error(
      'frontend/static-site/ has no snapshot. Run `uv run firm-export-site` ' +
        'from the repository root, then build again.',
    );
    process.exit(1);
  }
  try {
    await download(url);
  } catch (error) {
    console.error(`Could not get the site data: ${error.message}`);
    process.exit(1);
  }
  if (!existsSync(`${source}data/firms.json`)) {
    console.error('The downloaded site data has no data/firms.json.');
    process.exit(1);
  }
}

cpSync(source, target, { recursive: true });
if (existsSync(mapCode)) cpSync(mapCode, `${target}static/`, { recursive: true });
console.log('Copied the firm-export-site snapshot into dist/.');
