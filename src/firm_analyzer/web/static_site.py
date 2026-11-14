#!/usr/bin/env python3
"""
Snapshot the read-only viewer as static files, for hosting without Flask.

`firm-export-site` asks the Flask API (through its test client) for everything
the viewer's read-only pages show, and writes the answers as files:

    data/results-summary.json   GET /api/results/summary (counted from the firms below)
    data/taxonomy.json          GET /api/taxonomy
    data/firms.json             GET /api/firms, plus each firm's file id and summary
                                prose, so the browser can search without a server
    data/firms/<id>.json        GET /api/firms/<category>/<firm>
    data/firms_export.csv       GET /api/export.csv
    map/index.html, static/     GET /map and the files it loads

The frontend's static build (`npm run build:static`, see frontend/vercel.json)
copies them into the site. Only what the API already serves is written, so
raw_search.json (scraped pages) never leaves the machine.
"""

import argparse
import hashlib
import json
import os
import shutil
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import quote

from firm_analyzer.config import BASE_DIR
from firm_analyzer.core.results import plain_text, summary_body, with_notice

DEFAULT_OUT = BASE_DIR / "frontend" / "static-site"
#: Subfolders this command owns. They are rebuilt on every run, so a firm
#: removed from firm_results/ disappears from the next deploy.
OWNED_DIRS = ("data", "map", "static")


class ExportError(RuntimeError):
    """The API refused a request the snapshot needs, or there is nothing to publish."""


def firm_id(category_id: str, name: str) -> str:
    """A stable, URL-safe file name for a firm. Names are Korean, with brackets and spaces."""
    return hashlib.sha1(f"{category_id}/{name}".encode("utf-8")).hexdigest()[:16]


def _get(client, path: str):
    response = client.get(path)
    if response.status_code != 200:
        raise ExportError(f"GET {path} returned HTTP {response.status_code}")
    return response


def _write_json(path: Path, data) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    path.write_bytes(payload)
    return len(payload)


def export_site(out_dir: Path) -> dict:
    """Write the snapshot into `out_dir` and return what was written."""
    # Imported here because importing the app loads .env and builds the Flask app.
    from firm_analyzer.web import app as web

    client = web.app.test_client()
    config = web.load_config()
    taxonomy = web._load_taxonomy_or_none()

    rows = _get(client, "/api/firms").get_json()["firms"]
    if not rows:
        raise ExportError("No summarized firms to publish. Run firm-summarize first.")

    for name in OWNED_DIRS:
        shutil.rmtree(out_dir / name, ignore_errors=True)
    data_dir = out_dir / "data"

    for row in rows:
        detail_path = f"/api/firms/{quote(row['category_id'], safe='')}/{quote(row['name'], safe='')}"
        detail = _get(client, detail_path).get_json()
        row["id"] = firm_id(row["category_id"], row["name"])
        # What the API's search matches against; the browser builds snippets from it.
        row["text"] = plain_text(summary_body(detail["summary"], detail["segmentation"], taxonomy))
        row.pop("snippet", None)
        if detail["summary"].strip():
            detail["summary"] = with_notice(detail["summary"])
        _write_json(data_dir / "firms" / f"{row['id']}.json", detail)

    index_bytes = _write_json(data_dir / "firms.json", {"firms": rows})

    # Counted from the exported rows rather than read from /api/results/summary,
    # which may come from Supabase: the dashboard has to agree with the list.
    counts = Counter(row["category_id"] for row in rows)
    summary = {
        cat["id"]: {
            "name": cat.get("name", cat["id"]),
            "count": counts.get(cat["id"], 0),
            "color": cat.get("color", "#607D8B"),
        }
        for cat in config.get("categories", [])
        if cat.get("id")
    }
    summary["total"] = len(rows)
    _write_json(data_dir / "results-summary.json", summary)

    _write_json(data_dir / "taxonomy.json", _get(client, "/api/taxonomy").get_json())
    (data_dir / "firms_export.csv").write_bytes(_get(client, "/api/export.csv").data)

    map_dir = out_dir / "map"
    map_dir.mkdir(parents=True, exist_ok=True)
    (map_dir / "index.html").write_bytes(_get(client, "/map").data)
    shutil.copytree(web.STATIC_DIR, out_dir / "static")

    kakao_enabled = config.get("app", {}).get("enable_kakao_map", True)
    return {
        "firms": len(rows),
        "index_bytes": index_bytes,
        "kakao_key_missing": bool(kakao_enabled) and not os.getenv("KAKAO_JS_API_KEY"),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Snapshot the read-only viewer (dashboard, search, summaries, map, CSV) "
        "as static files for hosting without the Flask server"
    )
    parser.add_argument(
        "-o", "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Output folder (default: {DEFAULT_OUT.relative_to(BASE_DIR)})",
    )
    args = parser.parse_args()
    out_dir = args.out.expanduser().resolve()

    try:
        result = export_site(out_dir)
    except ExportError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Wrote {result['firms']} firms to {out_dir} "
          f"(firms.json {result['index_bytes'] / 1_000_000:.1f} MB).")
    if result["kakao_key_missing"]:
        print("Warning: KAKAO_JS_API_KEY is not set, so the map page will not load a map.",
              file=sys.stderr)
    print("Everything in it will be public once deployed: AI-written summaries about real "
          "companies, with the AI-generated notice.")
    print("Deploy: cd frontend && npx vercel build --prod && npx vercel deploy --prebuilt --prod")


if __name__ == "__main__":
    main()
