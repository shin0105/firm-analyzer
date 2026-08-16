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
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_cors import CORS
from supabase import create_client

from src.firm_analyzer.config import load_config, save_config, get_default_config, BASE_DIR

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
CORS(app)

# Configurable timeout values (in seconds)
FILTER_SCRIPT_TIMEOUT = int(os.getenv("FILTER_SCRIPT_TIMEOUT", "60"))
SUMMARIZE_SCRIPT_TIMEOUT = int(os.getenv("SUMMARIZE_SCRIPT_TIMEOUT", "300"))
DRY_RUN_TIMEOUT = int(os.getenv("DRY_RUN_TIMEOUT", "60"))

def get_results_summary():
    """Get summary of processed results."""
    config = load_config()
    output_dir = BASE_DIR / config.get("output", {}).get("directory", "firm_results")
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
    """Get list of firms in a category."""
    config = load_config()
    output_dir = BASE_DIR / config.get("output", {}).get("directory", "firm_results")
    cat_path = output_dir / category_id

    firms = []
    if cat_path.is_dir():
        for firm_dir in cat_path.iterdir():
            if firm_dir.is_dir():
                summary_path = firm_dir / "summary.md"
                summary_content = ""
                if summary_path.exists():
                    with open(summary_path, "r", encoding="utf-8") as f:
                        summary_content = f.read()

                firms.append(
                    {"name": firm_dir.name, "summary": summary_content, "path": str(firm_dir)}
                )

    return sorted(firms, key=lambda x: x["name"])

def get_available_columns():
    """Get available columns from input CSV."""
    from src.firm_analyzer.config import DEFAULT_INPUT_CSV
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

@app.route("/api/columns", methods=["GET"])
def get_columns():
    return jsonify({"columns": get_available_columns()})

@app.route("/api/run/filter", methods=["POST"])
def run_filter():
    try:
        script_path = BASE_DIR / "scripts" / "run_filter.py"
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True, text=True, timeout=FILTER_SCRIPT_TIMEOUT
        )
        return jsonify({"success": result.returncode == 0, "stdout": result.stdout, "stderr": result.stderr})
    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "error": "Script timed out"}), 408
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/run/summarize", methods=["POST"])
def run_summarize():
    data = request.get_json() or {}
    dry_run = data.get("dry_run", True)
    limit = data.get("limit", 5)

    try:
        script_path = BASE_DIR / "scripts" / "run_summarize.py"
        cmd = [sys.executable, str(script_path)]
        if dry_run: cmd.append("--dry-run")
        if limit: cmd.extend(["--limit", str(limit)])

        timeout = DRY_RUN_TIMEOUT if dry_run else SUMMARIZE_SCRIPT_TIMEOUT
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return jsonify({"success": result.returncode == 0, "stdout": result.stdout, "stderr": result.stderr})
    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "error": "Script timed out"}), 408
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/upload-pdf", methods=["POST"])
def upload_pdf():
    if 'file' not in request.files: return jsonify({"success": False, "error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '': return jsonify({"success": False, "error": "No selected file"}), 400
        
    if file and file.filename.endswith('.pdf'):
        provider = request.form.get('provider', 'gemini')
        temp_path = BASE_DIR / "data" / file.filename
        os.makedirs(temp_path.parent, exist_ok=True)
        file.save(str(temp_path))
        
        try:
            from src.firm_analyzer.core import pdf_parser_llm
            output_csv = pdf_parser_llm.parse_pdf_to_csv(str(temp_path), provider=provider)
            return jsonify({"success": True, "message": "Successfully parsed PDF to CSV.", "output_file": output_csv})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    return jsonify({"success": False, "error": "Invalid file type, must be PDF"}), 400

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
    print("Starting Firm Analyzer Web Application...")
    print("Open http://localhost:8001 in your browser")
    if debug_mode: print("WARNING: Debug mode is enabled. Do not use in production.")
    app.run(debug=debug_mode, host="0.0.0.0", port=8001)

if __name__ == "__main__":
    main()
