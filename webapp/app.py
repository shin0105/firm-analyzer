"""
Flask application for hosting the Firm Viewer webpage.
"""

from flask import Flask, render_template, send_from_directory
import os

app = Flask(__name__)


@app.route("/")
def index():
    """Serve the main firms viewer page."""
    return render_template("firms_viewer.html")


@app.route("/firm-viewer")
def firm_viewer():
    """Serve the alternative firm viewer page."""
    return render_template("firm_viewer.html")


@app.route("/data/<path:filename>")
def serve_data(filename):
    """Serve data files from the data directory."""
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    return send_from_directory(data_dir, filename)


if __name__ == "__main__":
    # Debug mode should only be enabled in development
    # Set FLASK_DEBUG=1 environment variable to enable debug mode
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug_mode, host="0.0.0.0", port=5000)
