import json
import os
from pathlib import Path

import yaml

def _find_base_dir() -> Path:
    """Locate the project root that holds config.yml, data/ and firm_results/.

    Resolution order:
      1. $FIRM_ANALYZER_HOME, for installed or containerised deployments.
      2. The repository root, when running from a source checkout
         (src/firm_analyzer/config.py -> firm_analyzer -> src -> root).
      3. The current working directory, as a last resort.

    Step 2 must be guarded: once the package is pip-installed, walking three
    parents up lands inside site-packages rather than a project root.
    """
    env_home = os.getenv("FIRM_ANALYZER_HOME")
    if env_home:
        return Path(env_home).expanduser().resolve()

    checkout_root = Path(__file__).resolve().parent.parent.parent
    if (checkout_root / "config.yml").exists() or (checkout_root / "pyproject.toml").exists():
        return checkout_root

    return Path.cwd()


BASE_DIR = _find_base_dir()
CONFIG_PATH = BASE_DIR / "config.yml"
# The hand-off between the two pipeline stages: the filter writes it and
# summarize reads it, so both default to this one path.
FILTERED_CSV = BASE_DIR / "data" / "filtered_firms.csv"


def results_dir(config: dict) -> Path:
    """Where per-firm result folders live (`output.directory`, relative to BASE_DIR)."""
    return BASE_DIR / config.get("output", {}).get("directory", "firm_results")

def get_default_config():
    """Return default configuration."""
    return {
        "app": {
            "data_source": "csv",
            "enable_kakao_map": True,
            # Which LLM back end to run. Overridden by the LLM_PROVIDER env var
            # and by --provider on the CLIs. See firm_analyzer.llm.
            "llm_provider": "openai",
            # Per-provider model override; empty means use the provider default.
            "llm_models": {
                "openai": "",
                "claude": "",
                "gemini": "",
                "github": "",
            },
            "summary_config_path": ""
        },
        "data": {
            # The 인원배정 list (a CSV in data/) the filter starts from. Empty
            # means the newest <year>_전문연구요원_인원배정.csv. Set it from the
            # 명단 관리 page or with `firm-roster activate`.
            "roster": "",
        },
        "segmentation": {
            # Multi-axis classification against taxonomy.yml, produced in the
            # same model call as the summary.
            "enabled": True,
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

def load_config():
    """Load configuration from YAML file, with fallback to JSON."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or get_default_config()
    
    # Fallback to config.json for legacy migration
    json_path = BASE_DIR / "config.json"
    if json_path.exists():
        with open(json_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        save_config(config)
        return config
        
    return get_default_config()

def save_config(config):
    """Save configuration to YAML file."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
