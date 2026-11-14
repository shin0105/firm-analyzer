// Last step of `npm run build:static`: copy the snapshot written by
// `uv run firm-export-site` (data/, map/, static/) into the build.
import { cpSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const source = fileURLToPath(new URL('../static-site/', import.meta.url));
const target = fileURLToPath(new URL('../dist/', import.meta.url));

if (!existsSync(`${source}data/firms.json`)) {
  console.error(
    'frontend/static-site/ has no snapshot. Run `uv run firm-export-site` ' +
      'from the repository root, then build again.',
  );
  process.exit(1);
}

cpSync(source, target, { recursive: true });
console.log('Copied the firm-export-site snapshot into dist/.');
