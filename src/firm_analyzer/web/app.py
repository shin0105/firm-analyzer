#!/usr/bin/env python3
"""
Firm Analyzer web application.

A Flask JSON API for the React frontend (frontend/), which it also serves at
"/" once built (`npm run build`), plus the map view at /map.

- Configuration, results, firm search and CSV export
- The yearly 인원배정 list: import, compare, activate (see core/roster.py)
- Filter, summarize and segment as background jobs (see jobs.py)
"""

import atexit
import os
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Optional
from urllib.parse import quote

from dotenv import load_dotenv
from flask import Flask, Response, abort, jsonify, render_template, request, send_from_directory
from flask_cors import CORS

from firm_analyzer.config import load_config, save_config, get_default_config, results_dir, BASE_DIR
from firm_analyzer.core import roster
from firm_analyzer.llm import PROVIDER_IDS, describe_providers, resolve_provider_id
from firm_analyzer.core.results import (
    iter_firm_dirs,
    load_json,
    parse_summary_header,
    plain_text,
    read_text,
    resolve_firm_dir,
    snippet,
    summary_body,
)
from firm_analyzer.web.jobs import JobConflict, JobError, JobManager, build_steps

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase_client = None
if SUPABASE_URL and SUPABASE_KEY:
    from supabase import create_client

    supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Define paths
WEB_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"
#: The React build, served at "/" when present. `npm run dev` proxies to this API instead.
FRONTEND_DIST = Path(os.getenv("FRONTEND_DIST", str(BASE_DIR / "frontend" / "dist")))

app = Flask(__name__, static_folder=None, template_folder=str(TEMPLATE_DIR))
# Send Korean as UTF-8 rather than \uXXXX escapes, which roughly halves the
# size of firm lists and summaries.
app.json.ensure_ascii = False

# Only allow the frontend dev server by default. This API has no authentication
# and can start subprocesses, so a wildcard origin would let any site the user
# visits drive it over localhost. The dev server proxies /api, so this only
# matters when VITE_API_BASE points the frontend at another origin.
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if o.strip()
]
CORS(app, origins=ALLOWED_ORIGINS)

# Reject oversized uploads before they are buffered to disk.
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_UPLOAD_BYTES", str(32 * 1024 * 1024)))

# Pipeline runs started from the UI. Running jobs are terminated with the
# server so no orphaned summarize keeps spending API quota.
jobs = JobManager()
atexit.register(jobs.shutdown)

#: File types the 명단 import accepts.
UPLOAD_EXTENSIONS = (".pdf", ".csv")


def safe_upload_name(raw_name: str, extensions: tuple = UPLOAD_EXTENSIONS) -> Optional[str]:
    """Reduce a client-supplied upload name to a bare, safe filename.

    Werkzeug preserves whatever the client sends, including "../" segments, so
    an unchecked name escapes the target directory. We deliberately avoid
    werkzeug's secure_filename here because it strips non-ASCII characters and
    every input list in this project has a Korean name.
    """
    if not raw_name:
        return None

    # Discard any directory component the client tried to smuggle in.
    candidate = PurePosixPath(raw_name.replace("\\", "/")).name
    candidate = candidate.strip().replace("\x00", "")

    if not candidate or candidate in {".", ".."}:
        return None
    if candidate.startswith("."):
        return None
    if not candidate.lower().endswith(extensions):
        return None

    return candidate


def valid_category_ids(config: dict) -> set:
    """The set of category ids the config actually declares."""
    return {c["id"] for c in config.get("categories", []) if c.get("id")}


def get_results_summary():
    """Number of processed firms per category."""
    config = load_config()
    output_dir = results_dir(config)

    summary = {}
    total = 0
    for cat in config.get("categories", []):
        cat_path = output_dir / cat["id"]
        count = len([d for d in cat_path.iterdir() if d.is_dir()]) if cat_path.is_dir() else 0
        summary[cat["id"]] = {
            "name": cat["name"],
            "count": count,
            "color": cat.get("color", "#607D8B"),
        }
        total += count

    summary["total"] = total
    return summary


def get_firms_by_category(category_id):
    """Get list of firms in a category.

    `category_id` arrives straight from the URL, so it is checked against the
    configured ids rather than being joined onto a path as-is; otherwise
    "/api/results/.." walks out of the results directory.
    """
    config = load_config()
    if category_id not in valid_category_ids(config):
        return []

    cat_path = results_dir(config) / category_id

    firms = []
    if cat_path.is_dir():
        for firm_dir in cat_path.iterdir():
            if firm_dir.is_dir():
                segmentation = load_json(firm_dir / "segmentation.json")
                # Deliberately no absolute path here: it would leak the
                # server's filesystem layout to every API consumer.
                firms.append({
                    "name": firm_dir.name,
                    "summary": read_text(firm_dir / "summary.md"),
                    "segmentation": segmentation if isinstance(segmentation, dict) else None,
                })

    return sorted(firms, key=lambda x: x["name"])


class BadFilter(ValueError):
    """A /api/firms query parameter that names no configured id."""


def _load_taxonomy_or_none() -> Optional[dict]:
    try:
        from firm_analyzer.core.segmentation import load_taxonomy

        return load_taxonomy()
    except Exception as e:
        print(f"Could not load taxonomy: {e}", file=sys.stderr)
        return None


def parse_firm_filters(args, config: dict, taxonomy: Optional[dict]) -> dict:
    """Validate /api/firms query parameters against config and taxonomy ids."""
    filters = {key: (args.get(key) or "").strip() for key in
               ("q", "category", "sector", "vertical", "business_model", "confidence", "segmented")}

    if filters["category"] and filters["category"] not in valid_category_ids(config):
        raise BadFilter(f"Unknown category: {filters['category']}")

    axes = {"sector": "sectors", "vertical": "verticals", "business_model": "business_models"}
    for param, section in axes.items():
        value = filters[param]
        if not value:
            continue
        if taxonomy is None:
            raise BadFilter("The segmentation taxonomy could not be loaded")
        allowed = {entry.get("id") for entry in taxonomy.get(section) or [] if isinstance(entry, dict)}
        if value not in allowed:
            raise BadFilter(f"Unknown {param}: {value}")

    levels = (taxonomy or {}).get("confidence_levels") or ["high", "medium", "low"]
    if filters["confidence"] and filters["confidence"] not in levels:
        raise BadFilter(f"Unknown confidence: {filters['confidence']}")

    segmented = filters["segmented"].lower()
    if segmented in ("", "any"):
        filters["segmented"] = None
    elif segmented in ("true", "1", "yes"):
        filters["segmented"] = True
    elif segmented in ("false", "0", "no"):
        filters["segmented"] = False
    else:
        raise BadFilter(f"segmented must be true or false, not {filters['segmented']}")

    return filters


def _matches_segmentation(segmentation: Optional[dict], filters: dict) -> bool:
    if filters["segmented"] is not None and (segmentation is not None) != filters["segmented"]:
        return False
    if not (filters["sector"] or filters["vertical"] or filters["business_model"] or filters["confidence"]):
        return True
    if segmentation is None:
        return False
    if filters["sector"] and segmentation.get("sector") != filters["sector"]:
        return False
    if filters["vertical"] and filters["vertical"] not in (segmentation.get("verticals") or []):
        return False
    if filters["business_model"] and segmentation.get("business_model") != filters["business_model"]:
        return False
    confidence = segmentation.get("confidence") or {}
    if filters["confidence"] and confidence.get("sector") != filters["confidence"]:
        return False
    return True


def search_firms(config: dict, filters: dict, taxonomy: Optional[dict]) -> tuple[list, int]:
    """Light rows for every firm folder that passes `filters`, plus the number scanned.

    Sorted by firm name across categories, except that firms whose name
    matches `q` come before those that only match in their summary text.
    """
    names = {cat["id"]: cat.get("name", cat["id"]) for cat in config.get("categories", []) if cat.get("id")}
    category_ids = [filters["category"]] if filters["category"] else list(names)
    needle = filters["q"].casefold()

    rows = []
    total = 0
    for category_id, firm_dir in iter_firm_dirs(results_dir(config), category_ids):
        if firm_dir.is_symlink():
            continue  # summarize never writes one, and firm_detail refuses them
        total += 1
        segmentation = load_json(firm_dir / "segmentation.json")
        segmentation = segmentation if isinstance(segmentation, dict) else None
        if not _matches_segmentation(segmentation, filters):
            continue

        text = read_text(firm_dir / "summary.md")
        name_match = bool(needle) and needle in firm_dir.name.casefold()
        if needle and not name_match and needle not in text.casefold():
            continue

        seg_record = segmentation or {}
        rows.append(((not name_match, firm_dir.name, category_id), {
            "name": firm_dir.name,
            "category_id": category_id,
            "category": names[category_id],
            "address": parse_summary_header(text).fields.get("Address", ""),
            "segmented": segmentation is not None,
            "sector": seg_record.get("sector") or None,
            "subsector": seg_record.get("subsector") or None,
            "verticals": seg_record.get("verticals") or [],
            "business_model": seg_record.get("business_model") or None,
            "sector_confidence": (seg_record.get("confidence") or {}).get("sector") or None,
            "snippet": snippet(plain_text(summary_body(text, segmentation, taxonomy)), filters["q"]),
        }))

    rows.sort(key=lambda row: row[0])
    return [row for _, row in rows], total


def get_available_columns():
    """Columns of the active 인원배정 list, for the filter column picker."""
    path = roster.active_roster_path(load_config())
    if path is None or not path.exists():
        return []
    return roster.normalize_columns(roster.read_roster(path).columns)


def _attachment(filename: str) -> str:
    """A Content-Disposition value that survives a Korean filename (RFC 5987)."""
    return f"attachment; filename=\"download.csv\"; filename*=UTF-8''{quote(filename)}"


def _busy_response():
    """409 while a background job may be reading or writing the same files."""
    active = jobs.active()
    if active is None:
        return None
    return jsonify({
        "success": False,
        "error": f"A {active.kind} job is already running.",
        "active": active.id,
    }), 409


# ---------------------------------------------------------------------------
# Configuration and results
# ---------------------------------------------------------------------------

@app.route("/api/config", methods=["GET"])
def get_config():
    return jsonify(load_config())


@app.route("/api/config", methods=["POST"])
def update_config():
    try:
        save_config(request.get_json())
        return jsonify({"success": True, "message": "Configuration saved successfully"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/config/reset", methods=["POST"])
def reset_config():
    config = get_default_config()
    save_config(config)
    return jsonify({"success": True, "config": config})


@app.route("/api/results/summary", methods=["GET"])
def results_summary():
    config = load_config()
    source = config.get("app", {}).get("data_source", "csv")
    if source == "supabase" and supabase_client:
        try:
            response = supabase_client.table("firms").select("category").execute()
            data = response.data
            summary = {
                cat["id"]: {"name": cat["name"], "count": 0, "color": cat.get("color", "#607D8B")}
                for cat in config.get("categories", [])
            }
            for row in data:
                cat_id = row.get("category")
                if cat_id and cat_id in summary:
                    summary[cat_id]["count"] += 1
            summary["total"] = len(data)
            return jsonify(summary)
        except Exception as e:
            print(f"Error fetching from supabase: {e}", file=sys.stderr)

    return jsonify(get_results_summary())


@app.route("/api/results/<category_id>", methods=["GET"])
def results_by_category(category_id):
    config = load_config()
    if category_id not in valid_category_ids(config):
        return jsonify({"success": False, "error": "Unknown category"}), 404

    source = config.get("app", {}).get("data_source", "csv")
    if source == "supabase" and supabase_client:
        try:
            response = supabase_client.table("firms").select("name, summary_md, webpage").eq("category", category_id).execute()
            firms = [{"name": row.get("name"), "summary": row.get("summary_md") or "No summary available"} for row in response.data]
            firms = sorted(firms, key=lambda x: x["name"])
            return jsonify({"firms": firms, "count": len(firms)})
        except Exception as e:
            print(f"Error fetching from supabase: {e}", file=sys.stderr)

    firms = get_firms_by_category(category_id)
    return jsonify({"firms": firms, "count": len(firms)})


# The two /api/firms endpoints read the local result folders even when
# app.data_source is "supabase": segmentation.json lives only there, and the
# Supabase `firms` table has no segmentation columns to filter on.

@app.route("/api/firms", methods=["GET"])
def list_firms():
    """Search firms across categories; light rows only, no full summaries."""
    config = load_config()
    taxonomy = _load_taxonomy_or_none()
    try:
        filters = parse_firm_filters(request.args, config, taxonomy)
    except BadFilter as e:
        return jsonify({"success": False, "error": str(e)}), 400

    firms, total = search_firms(config, filters, taxonomy)
    return jsonify({"firms": firms, "count": len(firms), "total": total})


@app.route("/api/firms/<category_id>/<firm_name>", methods=["GET"])
def firm_detail(category_id, firm_name):
    """One firm's full summary.md and segmentation."""
    config = load_config()
    if category_id not in valid_category_ids(config):
        return jsonify({"success": False, "error": "Unknown category"}), 404

    firm_dir = resolve_firm_dir(results_dir(config) / category_id, firm_name)
    if firm_dir is None:
        return jsonify({"success": False, "error": "Unknown firm"}), 404

    text = read_text(firm_dir / "summary.md")
    segmentation = load_json(firm_dir / "segmentation.json")
    category_name = next(
        (cat.get("name", category_id) for cat in config.get("categories", []) if cat.get("id") == category_id),
        category_id,
    )
    return jsonify({
        "name": firm_dir.name,
        "category_id": category_id,
        "category": category_name,
        "address": parse_summary_header(text).fields.get("Address", ""),
        "summary": text,
        "segmentation": segmentation if isinstance(segmentation, dict) else None,
    })


@app.route("/api/export.csv", methods=["GET"])
def export_csv():
    """Every processed firm as one CSV, rebuilt from the result folders."""
    from firm_analyzer.core.export import DEFAULT_EXPORT, export_csv_bytes

    return Response(
        export_csv_bytes(load_config()),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{DEFAULT_EXPORT}"'},
    )


@app.route("/api/columns", methods=["GET"])
def get_columns():
    return jsonify({"columns": get_available_columns()})


@app.route("/api/llm/providers", methods=["GET"])
def llm_providers():
    """The provider picker's data source.

    `configured` reflects whether the API key is actually present in the
    server's environment, so the UI can grey out a provider the user cannot run
    instead of letting them pick it and fail on the first request. Key values
    are never returned.
    """
    config = load_config()
    return jsonify(
        {
            "providers": describe_providers(config),
            "active": resolve_provider_id(None, config),
        }
    )


@app.route("/api/taxonomy", methods=["GET"])
def get_taxonomy():
    """The segmentation taxonomy, for rendering filters and labels."""
    try:
        from firm_analyzer.core.segmentation import load_taxonomy

        return jsonify(load_taxonomy())
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------------------------------------------------------------
# The yearly 인원배정 list (명단)
# ---------------------------------------------------------------------------

def _roster_error(exc: Exception, status: int = 400):
    return jsonify({"success": False, "error": str(exc)}), status


def _form_bool(name: str, default: bool) -> bool:
    value = request.form.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


@app.route("/api/rosters", methods=["GET"])
def list_rosters():
    """Every list in data/, newest year first, and which one the filter reads."""
    config = load_config()
    return jsonify({
        "rosters": [vars(info) for info in roster.list_rosters(config)],
        "active": roster.active_roster_name(config),
    })


@app.route("/api/rosters/import", methods=["POST"])
def import_roster():
    """Import a new list from an uploaded PDF or CSV.

    Form fields: file, year (optional when the filename holds it), method
    (rule | llm), provider (llm only), overwrite, activate. The AI method can
    take minutes on a long PDF; the frontend allows for that.
    """
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        return jsonify({"success": False, "error": "파일을 선택해 주세요."}), 400
    filename = safe_upload_name(upload.filename)
    if not filename:
        return jsonify({"success": False, "error": "PDF 또는 CSV 파일만 가져올 수 있습니다."}), 400

    method = request.form.get("method") or "rule"
    if method not in roster.IMPORT_METHODS:
        return jsonify({"success": False, "error": "Unknown method"}), 400
    provider = request.form.get("provider") or None
    if provider is not None and provider not in PROVIDER_IDS:
        return jsonify({"success": False, "error": "Unknown provider"}), 400

    activate = _form_bool("activate", True)
    if activate:
        busy = _busy_response()
        if busy:
            return busy

    # Parse from a private temp dir; only the normalised CSV (and the source
    # PDF, kept as provenance) land in data/.
    with tempfile.TemporaryDirectory() as work_dir:
        source = Path(work_dir) / filename
        upload.save(str(source))
        try:
            result = roster.import_roster(
                source,
                year=request.form.get("year") or None,
                method=method,
                provider=provider,
                overwrite=_form_bool("overwrite", False),
                activate=activate,
                config=load_config(),
            )
        except roster.RosterError as exc:
            return _roster_error(exc)
        except Exception as exc:
            # Provider errors can quote request details; keep them server-side.
            print(f"Roster import failed: {exc!r}", file=sys.stderr)
            return jsonify({"success": False, "error": "가져오기에 실패했습니다. 서버 로그를 확인해 주세요."}), 500

    return jsonify({"success": True, **result.to_dict()})


@app.route("/api/rosters/active", methods=["POST"])
def activate_roster():
    """Make a list the filter's input. Body: {"name": "<csv in data/>"}."""
    busy = _busy_response()
    if busy:
        return busy
    name = str((request.get_json(silent=True) or {}).get("name") or "")
    try:
        roster.set_active_roster(name, load_config())
    except roster.RosterError as exc:
        return _roster_error(exc)
    return jsonify({"success": True, "active": name})


@app.route("/api/rosters/compare", methods=["GET"])
def compare_rosters():
    """Firms new in `target`, gone from `base`, and the count in both."""
    try:
        diff = roster.compare_rosters(request.args.get("base", ""), request.args.get("target", ""))
    except roster.RosterError as exc:
        return _roster_error(exc)
    return jsonify(diff.to_dict())


@app.route("/api/rosters/compare.csv", methods=["GET"])
def compare_rosters_csv():
    """One side of a comparison (`part` = added | removed) as a CSV download."""
    part = request.args.get("part", "added")
    try:
        diff = roster.compare_rosters(request.args.get("base", ""), request.args.get("target", ""))
        body = roster.diff_csv_bytes(diff, part)
    except roster.RosterError as exc:
        return _roster_error(exc)
    label = "신규" if part == "added" else "제외"
    filename = f"{Path(diff.base).stem}_vs_{Path(diff.target).stem}_{label}.csv"
    return Response(body, mimetype="text/csv", headers={"Content-Disposition": _attachment(filename)})


@app.route("/api/rosters/<name>/download", methods=["GET"])
def download_roster(name):
    try:
        path = roster.roster_path(name)
    except roster.RosterError:
        abort(404)
    if not roster.is_roster_file(path):
        abort(404)
    return send_from_directory(str(path.parent), path.name, as_attachment=True)


# ---------------------------------------------------------------------------
# Background jobs
# ---------------------------------------------------------------------------

@app.route("/api/jobs", methods=["GET"])
def list_jobs():
    """Recent jobs, newest first, without their logs."""
    active = jobs.active()
    return jsonify({
        "jobs": [job.to_dict() for job in jobs.list()],
        "active": active.id if active else None,
    })


@app.route("/api/jobs", methods=["POST"])
def create_job():
    """Start filter, summarize, segment or pipeline (filter then summarize).

    Body: {"kind": "...", "options": {...}}. Returns 202 with the job, 400 for
    invalid options, 409 while another job is running.
    """
    data = request.get_json(silent=True) or {}
    kind = data.get("kind")
    options = data.get("options") or {}
    try:
        steps = build_steps(kind, options, load_config())
    except JobError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    try:
        job = jobs.start(kind, options, steps)
    except JobConflict as e:
        return jsonify({"success": False, "error": str(e), "active": e.active.id}), 409
    return jsonify(job.to_dict(since=0)), 202


@app.route("/api/jobs/<job_id>", methods=["GET"])
def job_status(job_id):
    """One job, with log lines from `?since=<n>` on, for incremental polling."""
    job = jobs.get(job_id)
    if job is None:
        return jsonify({"success": False, "error": "Unknown job"}), 404
    since = request.args.get("since", default=0, type=int)
    return jsonify(job.to_dict(since=max(since, 0)))


@app.route("/api/jobs/<job_id>/cancel", methods=["POST"])
def cancel_job(job_id):
    job = jobs.cancel(job_id)
    if job is None:
        return jsonify({"success": False, "error": "Unknown job"}), 404
    return jsonify(job.to_dict())


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@app.route("/map")
def map_viewer():
    """The Kakao map of the 인원배정 firms, embedded by the frontend's 지도 page."""
    config = load_config()
    return render_template(
        "firms_viewer.html",
        static_endpoint="serve_static",
        kakao_api_key=os.getenv("KAKAO_JS_API_KEY", ""),
        enable_kakao_map=config.get("app", {}).get("enable_kakao_map", True),
    )


@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory(str(STATIC_DIR), filename)


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(str(STATIC_DIR), "favicon.png", mimetype="image/png")


FRONTEND_MISSING = """<!doctype html><html lang="ko"><meta charset="utf-8">
<title>Firm Analyzer</title>
<body style="font-family:system-ui,sans-serif;max-width:40rem;margin:4rem auto;padding:0 1rem;line-height:1.6">
<h1>Firm Analyzer API</h1>
<p>The API is running, but the web interface has not been built yet.</p>
<p>Build it once with <code>cd frontend &amp;&amp; npm ci &amp;&amp; npm run build</code> and reload,
or run <code>npm run dev</code> in <code>frontend/</code> and open
<a href="http://localhost:5173">http://localhost:5173</a>.</p>
<p>See README.md for details.</p>
</body></html>"""


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def frontend(path):
    """The React app: built assets as files, every other path as index.html.

    Client-side routes (/pipeline, /rosters, ...) have no file of their own,
    so they fall back to index.html and the router takes over. Unknown /api
    paths stay 404 rather than returning HTML to a JSON client.
    """
    if path == "api" or path.startswith("api/"):
        return jsonify({"success": False, "error": "Not found"}), 404
    if not (FRONTEND_DIST / "index.html").is_file():
        return Response(FRONTEND_MISSING, mimetype="text/html")
    if path and (FRONTEND_DIST / path).is_file():
        return send_from_directory(str(FRONTEND_DIST), path)
    return send_from_directory(str(FRONTEND_DIST), "index.html")


def main():
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    # Loopback by default: these endpoints are unauthenticated and can start
    # subprocesses, so binding every interface exposes them to the network.
    # Override deliberately (e.g. FLASK_HOST=0.0.0.0 inside a container).
    host = os.getenv("FLASK_HOST", "127.0.0.1")
    port = int(os.getenv("FLASK_PORT", "8001"))

    print("Starting Firm Analyzer Web Application...")
    print(f"Open http://{'localhost' if host in ('127.0.0.1', '0.0.0.0') else host}:{port} in your browser")
    if debug_mode:
        print("WARNING: Debug mode is enabled. Do not use in production.")
    if host == "0.0.0.0":
        print("WARNING: Listening on all interfaces. This API has no authentication.")

    app.run(debug=debug_mode, host=host, port=port)


if __name__ == "__main__":
    main()
