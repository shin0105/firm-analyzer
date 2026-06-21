#!/usr/bin/env python3
"""
Firm Analyzer Web Application

A Flask-based web interface for:
- Managing filter and summary configuration
- Viewing processed firm results
- Running filter and summarize operations
"""

import json
import os
import subprocess
import sys
import yaml
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_cors import CORS
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase_client = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

CONFIG_PATH = "config.yml"
DEFAULT_INPUT_CSV = "2025_전문연구요원_인원배정.csv"
BASE_DIR = Path(__file__).parent
VIEWER_TEMPLATE_DIR = BASE_DIR / "webapp" / "templates"
VIEWER_STATIC_DIR = BASE_DIR / "webapp" / "static"

# Include the viewer templates so they can be rendered from this app
if app.jinja_loader and str(VIEWER_TEMPLATE_DIR) not in app.jinja_loader.searchpath:
    app.jinja_loader.searchpath.append(str(VIEWER_TEMPLATE_DIR))

# Configurable timeout values (in seconds)
FILTER_SCRIPT_TIMEOUT = int(os.getenv("FILTER_SCRIPT_TIMEOUT", "60"))
SUMMARIZE_SCRIPT_TIMEOUT = int(os.getenv("SUMMARIZE_SCRIPT_TIMEOUT", "300"))
DRY_RUN_TIMEOUT = int(os.getenv("DRY_RUN_TIMEOUT", "60"))


def load_config():
    """Load configuration from YAML file, with fallback to JSON."""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or get_default_config()
    elif os.path.exists("config.json"):
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        # Migrate to YAML
        save_config(config)
        return config
    return get_default_config()


def save_config(config):
    """Save configuration to YAML file."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def get_default_config():
    """Return default configuration."""
    return {
        "app": {
            "data_source": "csv",
            "enable_kakao_map": True,
            "model_selection": "gpt-4o",
            "summary_config_path": ""
        },
        "filters": {
            "location": {
                "enabled": True,
                "type": "contains",
                "values": ["서울"],
                "column": "소재지",
            }
        },
        "categories": [
            {
                "id": "finance",
                "name": "Finance/Quant",
                "description": "Finance, Financial Services, Quant Trading",
                "keywords": ["금융", "투자", "자산운용", "핀테크", "fintech", "quant"],
                "color": "#4CAF50",
            },
            {
                "id": "healthcare",
                "name": "Healthcare/Bio",
                "description": "Healthcare, Biotechnology, Medical",
                "keywords": ["의료", "바이오", "헬스케어", "제약", "병원", "의학"],
                "color": "#2196F3",
            },
            {
                "id": "ai_ml",
                "name": "AI/Machine Learning",
                "description": "Artificial Intelligence, Machine Learning, Deep Learning",
                "keywords": [
                    "인공지능",
                    "AI",
                    "머신러닝",
                    "딥러닝",
                    "자연어처리",
                    "NLP",
                ],
                "color": "#9C27B0",
            },
            {
                "id": "general",
                "name": "General",
                "description": "Other industries",
                "keywords": [],
                "color": "#607D8B",
            },
        ],
        "summary": {
            "language": "Korean",
            "focus_areas": ["business_areas", "research_technologies", "job_openings"],
            "custom_prompt": "",
            "output_format": "markdown",
            "system_prompt": "You are a helpful assistant that summarizes company information in JSON format.",
        },
        "search": {
            "query_template": "{firm_name} 채용 연구분야 사업내용",
            "search_depth": "advanced",
            "max_results": 5,
            "context": "",
        },
        "output": {"directory": "firm_results", "create_csv_summary": True},
    }


def get_results_summary():
    """Get summary of processed results."""
    config = load_config()
    output_dir = config.get("output", {}).get("directory", "firm_results")
    categories = config.get("categories", [])

    summary = {}
    total = 0

    for cat in categories:
        cat_path = os.path.join(output_dir, cat["id"])
        if os.path.isdir(cat_path):
            count = len(
                [
                    d
                    for d in os.listdir(cat_path)
                    if os.path.isdir(os.path.join(cat_path, d))
                ]
            )
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
    output_dir = config.get("output", {}).get("directory", "firm_results")
    cat_path = os.path.join(output_dir, category_id)

    firms = []
    if os.path.isdir(cat_path):
        for firm_dir in os.listdir(cat_path):
            firm_path = os.path.join(cat_path, firm_dir)
            if os.path.isdir(firm_path):
                summary_path = os.path.join(firm_path, "summary.md")
                summary_content = ""
                if os.path.exists(summary_path):
                    with open(summary_path, "r", encoding="utf-8") as f:
                        summary_content = f.read()

                firms.append(
                    {"name": firm_dir, "summary": summary_content, "path": firm_path}
                )

    return sorted(firms, key=lambda x: x["name"])


def get_available_columns():
    """Get available columns from input CSV."""
    if os.path.exists(DEFAULT_INPUT_CSV):
        import pandas as pd

        df = pd.read_csv(DEFAULT_INPUT_CSV, nrows=0)
        return list(df.columns)
    return []


@app.route("/")
def index():
    """Render the firm summary configuration editor page."""
    return render_template("config_firm_summary.html")


@app.route("/config/firm-summary")
def config_firm_summary():
    """Render the firm summary configuration editor page."""
    return render_template("config_firm_summary.html")


@app.route("/view/firm-summary")
def view_firm_summary():
    """Render the firm summary results viewing page."""
    return render_template("view_firm_summary.html")


@app.route("/firms")
def firms_viewer():
    """Render the map-based firm viewer page."""
    kakao_api_key = os.getenv("KAKAO_JS_API_KEY", "")
    config = load_config()
    enable_kakao_map = config.get("app", {}).get("enable_kakao_map", True)
    return render_template("firms_viewer.html", static_endpoint="viewer_static", kakao_api_key=kakao_api_key, enable_kakao_map=enable_kakao_map)


@app.route("/api/config", methods=["GET"])
def get_config():
    """Get current configuration."""
    config = load_config()
    return jsonify(config)


@app.route("/api/config", methods=["POST"])
def update_config():
    """Update configuration."""
    try:
        config = request.get_json()
        save_config(config)
        return jsonify({"success": True, "message": "Configuration saved successfully"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/config/reset", methods=["POST"])
def reset_config():
    """Reset configuration to defaults."""
    config = get_default_config()
    save_config(config)
    return jsonify({"success": True, "config": config})


@app.route("/api/results/summary", methods=["GET"])
def results_summary():
    """Get summary of processed results."""
    config = load_config()
    source = config.get("app", {}).get("data_source", "csv")
    if source == "supabase" and supabase_client:
        try:
            response = supabase_client.table("firms").select("category").execute()
            data = response.data
            
            config = load_config()
            categories = config.get("categories", [])
            summary = {}
            total = len(data)
            
            for cat in categories:
                summary[cat["id"]] = {
                    "name": cat["name"],
                    "count": 0,
                    "color": cat.get("color", "#607D8B"),
                }
                
            for row in data:
                cat_id = row.get("category")
                if cat_id and cat_id in summary:
                    summary[cat_id]["count"] += 1
                    
            summary["total"] = total
            return jsonify(summary)
        except Exception as e:
            print(f"Error fetching from supabase: {e}")
            
    summary = get_results_summary()
    return jsonify(summary)


@app.route("/api/results/<category_id>", methods=["GET"])
def results_by_category(category_id):
    """Get firms in a category."""
    config = load_config()
    source = config.get("app", {}).get("data_source", "csv")
    if source == "supabase" and supabase_client:
        try:
            response = supabase_client.table("firms").select("name, summary_md, webpage").eq("category", category_id).execute()
            firms = []
            for row in response.data:
                firms.append({
                    "name": row.get("name"),
                    "summary": row.get("summary_md") or "No summary available"
                })
            firms = sorted(firms, key=lambda x: x["name"])
            return jsonify({"firms": firms, "count": len(firms)})
        except Exception as e:
            print(f"Error fetching from supabase: {e}")
            
    firms = get_firms_by_category(category_id)
    return jsonify({"firms": firms, "count": len(firms)})


@app.route("/api/columns", methods=["GET"])
def get_columns():
    """Get available CSV columns."""
    columns = get_available_columns()
    return jsonify({"columns": columns})


@app.route("/api/run/filter", methods=["POST"])
def run_filter():
    """Run the filter script."""
    try:
        result = subprocess.run(
            [sys.executable, "filter_firms.py"],
            capture_output=True,
            text=True,
            timeout=FILTER_SCRIPT_TIMEOUT,
        )
        return jsonify(
            {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        )
    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "error": "Script timed out"}), 408
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/run/summarize", methods=["POST"])
def run_summarize():
    """Run the summarize script (dry-run by default)."""
    data = request.get_json() or {}
    dry_run = data.get("dry_run", True)
    limit = data.get("limit", 5)

    try:
        cmd = [sys.executable, "search_summarize.py"]
        if dry_run:
            cmd.append("--dry-run")
        if limit:
            cmd.extend(["--limit", str(limit)])

        timeout = DRY_RUN_TIMEOUT if dry_run else SUMMARIZE_SCRIPT_TIMEOUT
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return jsonify(
            {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        )
    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "error": "Script timed out"}), 408
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/upload-pdf", methods=["POST"])
def upload_pdf():
    """Upload a PDF file and parse it to CSV using LLM."""
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "error": "No selected file"}), 400
        
    if file and file.filename.endswith('.pdf'):
        provider = request.form.get('provider', 'gemini')
        # Save temporarily
        temp_path = os.path.join(BASE_DIR, "data", file.filename)
        os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
        file.save(temp_path)
        
        try:
            # Import here to avoid circular imports or missing modules during init
            import pdf_parser
            
            output_csv = pdf_parser.parse_pdf_to_csv(temp_path, provider=provider)
            return jsonify({
                "success": True, 
                "message": f"Successfully parsed PDF to CSV.",
                "output_file": output_csv
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    
    return jsonify({"success": False, "error": "Invalid file type, must be PDF"}), 400


@app.route("/api/download/<filename>", methods=["GET"])
def download_file(filename):
    """Download a parsed CSV file."""
    try:
        return send_from_directory(os.path.join(BASE_DIR, "data"), filename, as_attachment=True)
    except Exception as e:
        return jsonify({"success": False, "error": "File not found"}), 404


# Serve static files for the web app
@app.route("/static/<path:filename>")
def serve_static(filename):
    """Serve static files."""
    return send_from_directory("static", filename)


@app.route("/viewer-static/<path:filename>")
def viewer_static(filename):
    """Serve assets for the map-based firm viewer."""
    return send_from_directory(str(VIEWER_STATIC_DIR), filename)


@app.route("/favicon.ico")
def favicon():
    """Serve favicon."""
    return send_from_directory("static", "favicon.png", mimetype="image/png")


@app.route("/.well-known/appspecific/com.chrome.devtools.json")
def chrome_devtools():
    """Suppress Chrome devtools 404 error in logs."""
    return jsonify({})


def create_templates():
    """Create template files if they don't exist."""
    templates_dir = Path("templates")
    templates_dir.mkdir(exist_ok=True)

    static_dir = Path("static")
    static_dir.mkdir(exist_ok=True)


if __name__ == "__main__":
    create_templates()
    # Debug mode is controlled by FLASK_DEBUG environment variable for security
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    print("Starting Firm Analyzer Web Application...")
    print("Open http://localhost:8001 in your browser")
    if debug_mode:
        print("WARNING: Debug mode is enabled. Do not use in production.")
    app.run(debug=debug_mode, host="0.0.0.0", port=8001)
