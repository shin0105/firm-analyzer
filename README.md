# Firm WebSearch

A web application for viewing and searching 2025 전문연구요원 인원배정 업체 현황 (Research Personnel Assignment Companies).

## Project Structure

```
firm_websearch/
├── data/                          # Data files (CSV)
│   ├── 2025_전문연구요원_인원배정.csv
│   └── seoul_firms.csv
├── firm_summary/                  # Firm data processing scripts
│   ├── 1_filter_seoul.py          # Filter Seoul-based firms
│   ├── 2_search_summarize.py      # Search and summarize firm info
│   ├── filter_seoul_firms.py      # Alternative filtering script
│   ├── generate_firms_data.py     # Generate JS data for webapp
│   └── test_url.py                # URL testing utility
├── firm_results/                  # Results from firm summarization
│   ├── finance/                   # Finance/Quant related firms
│   └── general/                   # General firms
├── webapp/                        # Flask web application
│   ├── app.py                     # Flask application entry point
│   ├── static/
│   │   ├── css/                   # Stylesheets
│   │   │   ├── firm_viewer.css
│   │   │   └── firms_viewer.css
│   │   └── js/                    # JavaScript files
│   │       ├── firm_viewer.js
│   │       ├── firms_viewer.js
│   │       └── firms_data.js
│   └── templates/                 # Jinja2 templates
│       ├── firm_viewer.html
│       └── firms_viewer.html
├── requirements.txt               # Python dependencies
└── README.md                      # This file
```

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/shin0105/firm_websearch.git
   cd firm_websearch
   ```

2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate     # Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Running the Web Application

Start the Flask development server:

```bash
cd webapp
python app.py
```

Then open your browser to:
- `http://localhost:5000/` - Main firms viewer
- `http://localhost:5000/firm-viewer` - Alternative firm viewer

### Running Firm Summary Scripts

1. **Filter Seoul firms:**
   ```bash
   cd firm_summary
   python 1_filter_seoul.py
   ```

2. **Search and summarize firms:**
   ```bash
   python 2_search_summarize.py
   ```

3. **Generate JS data for webapp:**
   ```bash
   python generate_firms_data.py
   ```

## Environment Variables

Create a `.env` file with the following variables for the summary scripts:

```
TAVILY_API_KEY=your_tavily_api_key
GITHUB_TOKEN=your_github_token
```

## Features

- Interactive map showing firm locations across Korea
- Region-based filtering (Seoul, Busan, etc.)
- Seoul district (구) filtering
- Search functionality
- Responsive design for mobile and desktop

## License

MIT License
