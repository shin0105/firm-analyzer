#!/usr/bin/env python3
"""
Firm Analyzer Web Application

A Flask-based web interface for:
- Managing filter and summary configuration
- Viewing processed firm results
- Running filter and summarize operations
"""

import os
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Optional

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request, send_from_directory
from flask_cors import CORS
from supabase import create_client

from firm_analyzer.config import load_config, save_config, get_default_config, results_dir, BASE_DIR
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

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase_client = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Define paths
WEB_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"

app = Flask(__name__, static_folder=str(STATIC_DIR), template_folder=str(TEMPLATE_DIR))
# Send Korean as UTF-8 rather than \uXXXX escapes, which roughly halves the
# size of firm lists and summaries.
app.json.ensure_ascii = False

# Only allow the frontend dev server by default. This API has no authentication
# and can start subprocesses, so a wildcard origin would let any site the user
# visits drive it over localhost.
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if o.strip()
]
CORS(app, origins=ALLOWED_ORIGINS)

# Reject oversized uploads before they are buffered to disk.
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_UPLOAD_BYTES", str(32 * 1024 * 1024)))

# Configurable timeout values (in seconds)
FILTER_SCRIPT_TIMEOUT = int(os.getenv("FILTER_SCRIPT_TIMEOUT", "60"))
SUMMARIZE_SCRIPT_TIMEOUT = int(os.getenv("SUMMARIZE_SCRIPT_TIMEOUT", "300"))
DRY_RUN_TIMEOUT = int(os.getenv("DRY_RUN_TIMEOUT", "60"))


def safe_upload_name(raw_name: str) -> Optional[str]:
    """Reduce a client-supplied upload name to a bare, safe filename.

    Werkzeug preserves whatever the client sends, including "../" segments, so
    an unchecked name escapes the data directory. We deliberately avoid
    werkzeug's secure_filename here because it strips non-ASCII characters and
    every input PDF in this project has a Korean name.
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
    if not candidate.lower().endswith(".pdf"):
        return None

    return candidate


def valid_category_ids(config: dict) -> set:
    """The set of category ids the config actually declares."""
    return {c["id"] for c in config.get("categories", []) if c.get("id")}

def get_results_summary():
    """Get summary of processed results."""
    config = load_config()
    output_dir = results_dir(config)
    categories = config.get("categories", [])

    summary = {}
    total = 0

    for cat in categories:
        cat_path = output_dir / cat["id"]
        if cat_path.is_dir():
            count = len([d for d in cat_path.iterdir() if d.is_dir()])
            summary[cat["id"]] = {
                "name": cat["name"],
                "count": count,
                "color": cat.get("color", "#607D8B"),
            }
            total += count
        else:
            summary[cat["id"]] = {
                "name": cat["name"],
                "count": 0,
                "color": cat.get("color", "#607D8B"),
            }

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
                summary_path = firm_dir / "summary.md"
                summary_content = ""
                if summary_path.exists():
                    with open(summary_path, "r", encoding="utf-8") as f:
                        summary_content = f.read()

                segmentation = load_json(firm_dir / "segmentation.json")

                # Deliberately no absolute path here: it would leak the
                # server's filesystem layout to every API consumer.
                firms.append({
                    "name": firm_dir.name,
                    "summary": summary_content,
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
    """Get available columns from input CSV."""
    from firm_analyzer.config import DEFAULT_INPUT_CSV
    if DEFAULT_INPUT_CSV.exists():
        import pandas as pd
        df = pd.read_csv(DEFAULT_INPUT_CSV, nrows=0)
        return list(df.columns)
    return []

@app.route("/")
def index():
    return render_template("config_firm_summary.html")

@app.route("/config/firm-summary")
def config_firm_summary():
    return render_template("config_firm_summary.html")

@app.route("/view/firm-summary")
def view_firm_summary():
    return render_template("view_firm_summary.html")

@app.route("/firms")
def firms_viewer():
    kakao_api_key = os.getenv("KAKAO_JS_API_KEY", "")
    config = load_config()
    enable_kakao_map = config.get("app", {}).get("enable_kakao_map", True)
    return render_template("firms_viewer.html", static_endpoint="serve_static", kakao_api_key=kakao_api_key, enable_kakao_map=enable_kakao_map)

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
            categories = config.get("categories", [])
            summary = {}
            total = len(data)
            for cat in categories:
                summary[cat["id"]] = {"name": cat["name"], "count": 0, "color": cat.get("color", "#607D8B")}
            for row in data:
                cat_id = row.get("category")
                if cat_id and cat_id in summary:
                    summary[cat_id]["count"] += 1
            summary["total"] = total
            return jsonify(summary)
        except Exception as e:
            print(f"Error fetching from supabase: {e}")
            
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
            print(f"Error fetching from supabase: {e}")
            
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

def _script_response(result):
    """Shape a subprocess result for the client.

    stdout is the script's own progress output and is safe to show. stderr is
    a Python traceback on failure, which carries absolute paths and sometimes
    fragments of API keys, so it is logged server-side instead of returned.
    """
    if result.returncode != 0:
        print(f"Script failed (exit {result.returncode}):\n{result.stderr}", file=sys.stderr)

    return jsonify({
        "success": result.returncode == 0,
        "stdout": result.stdout,
        "error": None if result.returncode == 0 else "Script failed; see server logs for details.",
    })

@app.route("/api/run/filter", methods=["POST"])
def run_filter():
    try:
        script_path = BASE_DIR / "scripts" / "run_filter.py"
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True, text=True, timeout=FILTER_SCRIPT_TIMEOUT
        )
        return _script_response(result)
    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "error": "Script timed out"}), 408
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/run/summarize", methods=["POST"])
def run_summarize():
    data = request.get_json() or {}
    dry_run = bool(data.get("dry_run", True))
    limit = data.get("limit", 5)

    if limit is not None:
        try:
            limit = int(limit)
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "limit must be an integer"}), 400
        if not 1 <= limit <= 10000:
            return jsonify({"success": False, "error": "limit out of range"}), 400

    provider = data.get("provider")
    if provider is not None:
        provider = str(provider)
        if provider not in PROVIDER_IDS:
            return jsonify({"success": False, "error": "Unknown provider"}), 400

    try:
        script_path = BASE_DIR / "scripts" / "run_summarize.py"
        cmd = [sys.executable, str(script_path)]
        if dry_run: cmd.append("--dry-run")
        if limit: cmd.extend(["--limit", str(limit)])
        if provider: cmd.extend(["--provider", provider])

        timeout = DRY_RUN_TIMEOUT if dry_run else SUMMARIZE_SCRIPT_TIMEOUT
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return _script_response(result)
    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "error": "Script timed out"}), 408
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/upload-pdf", methods=["POST"])
def upload_pdf():
    if 'file' not in request.files: return jsonify({"success": False, "error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '': return jsonify({"success": False, "error": "No selected file"}), 400
        
    filename = safe_upload_name(file.filename)
    if not filename:
        return jsonify({"success": False, "error": "Invalid file type, must be PDF"}), 400

    # Empty means "whatever config.yml selects"; anything else must be a known
    # provider id, since it reaches a subprocess-free but still keyed code path.
    provider = request.form.get('provider') or None
    if provider is not None and provider not in PROVIDER_IDS:
        return jsonify({"success": False, "error": "Unknown provider"}), 400

    data_dir = (BASE_DIR / "data").resolve()
    temp_path = (data_dir / filename).resolve()

    # Belt-and-braces: confirm the resolved path really is inside data/.
    if temp_path.parent != data_dir:
        return jsonify({"success": False, "error": "Invalid filename"}), 400

    data_dir.mkdir(parents=True, exist_ok=True)
    file.save(str(temp_path))

    try:
        from firm_analyzer.core import pdf_parser_llm
        output_csv = pdf_parser_llm.parse_pdf_to_csv(str(temp_path), provider=provider)
        return jsonify({"success": True, "message": "Successfully parsed PDF to CSV.", "output_file": output_csv})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/download/<filename>", methods=["GET"])
def download_file(filename):
    try:
        return send_from_directory(str(BASE_DIR / "data"), filename, as_attachment=True)
    except Exception:
        return jsonify({"success": False, "error": "File not found"}), 404

@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory(str(STATIC_DIR), filename)

@app.route("/favicon.ico")
def favicon():
    return send_from_directory(str(STATIC_DIR), "favicon.png", mimetype="image/png")

@app.route("/.well-known/appspecific/com.chrome.devtools.json")
def chrome_devtools():
    return jsonify({})

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
