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
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory

app = Flask(__name__, static_folder="static", template_folder="templates")

CONFIG_PATH = "config.json"
DEFAULT_INPUT_CSV = "2025_전문연구요원_인원배정.csv"

# Configurable timeout values (in seconds)
FILTER_SCRIPT_TIMEOUT = int(os.getenv("FILTER_SCRIPT_TIMEOUT", "60"))
SUMMARIZE_SCRIPT_TIMEOUT = int(os.getenv("SUMMARIZE_SCRIPT_TIMEOUT", "300"))
DRY_RUN_TIMEOUT = int(os.getenv("DRY_RUN_TIMEOUT", "60"))


def load_config():
    """Load configuration from JSON file."""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return get_default_config()


def save_config(config):
    """Save configuration to JSON file."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_default_config():
    """Return default configuration."""
    return {
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
        },
        "search": {
            "query_template": "{firm_name} 채용 연구분야 사업내용",
            "search_depth": "advanced",
            "max_results": 5,
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
    """Render main page."""
    return render_template("index.html")


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
    summary = get_results_summary()
    return jsonify(summary)


@app.route("/api/results/<category_id>", methods=["GET"])
def results_by_category(category_id):
    """Get firms in a category."""
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


# Serve static files for the web app
@app.route("/static/<path:filename>")
def serve_static(filename):
    """Serve static files."""
    return send_from_directory("static", filename)


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
