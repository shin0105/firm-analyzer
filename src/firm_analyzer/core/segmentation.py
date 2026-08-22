#!/usr/bin/env python3
"""Multi-axis firm segmentation: taxonomy loading, prompting, validation.

The classifier asks one model call to place a firm on five independent axes
(sector/subsector, technology verticals, business model, value-chain position,
organisation profile) and to cite its evidence per axis. `taxonomy.yml` holds
the labels and the tie-break rules; this module turns that file into a prompt
and turns the model's answer back into a validated record.

Two design choices worth knowing:

* **Single pass, whole taxonomy in the prompt.** A path-traversal scheme (pick
  the sector, then re-prompt for the subsector) costs one call per level and
  loses cross-axis consistency — the model can no longer notice that "fabless"
  in the subsector implies chip design on the vertical axis. The taxonomy is
  small enough to fit in one prompt, so it goes in whole.

* **Validation is not optional.** Model output is checked against the taxonomy
  ids and anything unrecognised degrades to `unknown` with low confidence,
  rather than inventing a label that would then leak into CSV columns and
  Supabase rows. A hallucinated category is worse than an admitted gap.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml

from firm_analyzer.config import BASE_DIR

TAXONOMY_FILENAME = "taxonomy.yml"

#: Axis defaults used whenever the model gives us something we cannot verify.
UNKNOWN = "unknown"
FALLBACK_SECTOR = "research_institute"
FALLBACK_SUBSECTOR = "other"

SEGMENTATION_SYSTEM_PROMPT = (
    "당신은 기업 산업분류 전문 애널리스트입니다. "
    "홍보 문구가 아니라 확인 가능한 근거(매출원, 제품, 고객, 조직)에 기반해 분류하고, "
    "근거가 없으면 unknown 을 선택합니다. 항상 지정된 JSON 형식만 출력합니다."
)


class TaxonomyError(RuntimeError):
    """Raised when taxonomy.yml is missing required structure."""


@lru_cache(maxsize=4)
def load_taxonomy(path: Optional[str] = None) -> dict:
    """Load and lightly validate taxonomy.yml."""
    taxonomy_path = Path(path) if path else BASE_DIR / TAXONOMY_FILENAME
    if not taxonomy_path.exists():
        raise TaxonomyError(
            f"{taxonomy_path} not found. It ships with the repository; restore it "
            "or point FIRM_ANALYZER_HOME at the project root."
        )

    with open(taxonomy_path, "r", encoding="utf-8") as handle:
        taxonomy = yaml.safe_load(handle) or {}

    for key in ("sectors", "verticals", "business_models", "value_chain", "profile"):
        if not taxonomy.get(key):
            raise TaxonomyError(f"taxonomy.yml is missing the '{key}' section.")
    return taxonomy


def _ids(entries: list) -> list[str]:
    return [entry["id"] for entry in entries if isinstance(entry, dict) and entry.get("id")]


def _label_map(entries: list) -> dict[str, str]:
    return {
        entry["id"]: entry.get("name", entry["id"])
        for entry in entries
        if isinstance(entry, dict) and entry.get("id")
    }


def sector_ids(taxonomy: dict) -> list[str]:
    return _ids(taxonomy["sectors"])


def subsector_ids(taxonomy: dict, sector_id: str) -> list[str]:
    for sector in taxonomy["sectors"]:
        if sector.get("id") == sector_id:
            return _ids(sector.get("subsectors") or [])
    return []


def profile_ids(taxonomy: dict, field: str) -> list[str]:
    return _ids(taxonomy["profile"].get(field) or [])


def labels(taxonomy: dict) -> dict[str, dict[str, str]]:
    """Every axis's id -> Korean label, for rendering."""
    sector_labels = _label_map(taxonomy["sectors"])
    subsector_labels: dict[str, str] = {}
    for sector in taxonomy["sectors"]:
        subsector_labels.update(_label_map(sector.get("subsectors") or []))
    return {
        "sector": sector_labels,
        "subsector": subsector_labels,
        "vertical": _label_map(taxonomy["verticals"]),
        "business_model": _label_map(taxonomy["business_models"]),
        "value_chain": _label_map(taxonomy["value_chain"]),
        "size_tier": _label_map(taxonomy["profile"].get("size_tier") or []),
        "rnd_intensity": _label_map(taxonomy["profile"].get("rnd_intensity") or []),
        "research_role": _label_map(taxonomy["profile"].get("research_role") or []),
    }


def taxonomy_digest(taxonomy: dict) -> str:
    """Render the taxonomy as the prompt's reference section.

    Keywords and `distinguish` rules are included because they are what turn a
    topical guess into a decision: the keywords anchor unfamiliar Korean
    industry terms, and the rules resolve the adjacent-sector cases.
    """
    lines: list[str] = ["## 축 1. 산업 섹터 / 세부섹터 (하나만 선택)"]
    for sector in taxonomy["sectors"]:
        keywords = ", ".join(sector.get("keywords") or [])
        lines.append(
            f"- {sector['id']} — {sector.get('name', '')}"
            + (f" | 키워드: {keywords}" if keywords else "")
        )
        for sub in sector.get("subsectors") or []:
            sub_keywords = ", ".join(sub.get("keywords") or [])
            lines.append(
                f"    - {sub['id']} — {sub.get('name', '')}"
                + (f" ({sub_keywords})" if sub_keywords else "")
            )
        for rule in sector.get("distinguish") or []:
            lines.append(f"    · 구분기준: {rule}")

    lines.append("")
    max_verticals = taxonomy.get("max_verticals", 3)
    lines.append(f"## 축 2. 기술 버티컬 (0~{max_verticals}개, 섹터와 직교)")
    for vertical in taxonomy["verticals"]:
        keywords = ", ".join(vertical.get("keywords") or [])
        lines.append(
            f"- {vertical['id']} — {vertical.get('name', '')}"
            + (f" ({keywords})" if keywords else "")
        )
    for rule in taxonomy.get("vertical_rules") or []:
        lines.append(f"· {rule}")

    lines.append("")
    lines.append("## 축 3. 사업모델 (하나만 선택)")
    for model in taxonomy["business_models"]:
        signal = model.get("signal")
        lines.append(
            f"- {model['id']} — {model.get('name', '')}" + (f" | 판단신호: {signal}" if signal else "")
        )
    for rule in taxonomy.get("business_model_rules") or []:
        lines.append(f"· {rule}")

    lines.append("")
    lines.append("## 축 4. 밸류체인 위치 (하나만 선택)")
    for stage in taxonomy["value_chain"]:
        lines.append(f"- {stage['id']} — {stage.get('name', '')}")

    lines.append("")
    lines.append("## 축 5. 조직 프로파일")
    for field in ("size_tier", "rnd_intensity", "research_role"):
        options = taxonomy["profile"].get(field) or []
        rendered = ", ".join(
            f"{opt['id']}({opt.get('name', '')})" for opt in options if opt.get("id")
        )
        lines.append(f"- {field}: {rendered}")

    lines.append("")
    lines.append("## 공통 판단 규칙")
    for rule in taxonomy.get("rules") or []:
        lines.append(f"· {rule}")

    return "\n".join(lines)


def output_contract(taxonomy: dict, language: str = "Korean") -> str:
    """The JSON shape the model must return for the segmentation block."""
    max_verticals = taxonomy.get("max_verticals", 3)
    return f"""
"segmentation" 객체는 정확히 다음 구조를 따릅니다.

{{
  "sector": "축1의 섹터 id",
  "subsector": "선택한 섹터에 속한 세부섹터 id (모르면 null)",
  "verticals": ["축2의 id", "최대 {max_verticals}개"],
  "business_model": "축3의 id",
  "value_chain": "축4의 id",
  "profile": {{
    "size_tier": "id",
    "rnd_intensity": "id",
    "research_role": "id"
  }},
  "confidence": {{
    "sector": "high|medium|low",
    "verticals": "high|medium|low",
    "business_model": "high|medium|low",
    "value_chain": "high|medium|low",
    "profile": "high|medium|low"
  }},
  "evidence": {{
    "sector": "{language} 한 문장 근거 (가능하면 출처 URL 포함)",
    "business_model": "{language} 한 문장 근거",
    "verticals": "{language} 한 문장 근거"
  }},
  "signals": ["분류 근거가 된 핵심 키워드 3~8개"]
}}
""".strip()


def build_segmentation_section(taxonomy: dict, language: str = "Korean") -> str:
    """The full segmentation instruction block, for embedding in a prompt."""
    return (
        "다음 분류체계에 따라 이 업체를 다축 분류하십시오.\n\n"
        f"{taxonomy_digest(taxonomy)}\n\n"
        f"{output_contract(taxonomy, language)}"
    )


def build_segmentation_prompt(
    firm_name: str,
    search_results: list,
    taxonomy: dict,
    language: str = "Korean",
    webpage: Optional[dict] = None,
    extra_context: str = "",
) -> str:
    """A standalone segmentation prompt (used when re-classifying only)."""
    webpage_line = ""
    if webpage and webpage.get("url"):
        webpage_line = f"\n공식 홈페이지: {webpage['url']}"

    return f"""
업체명: {firm_name}{webpage_line}

{build_segmentation_section(taxonomy, language)}

최상위 JSON은 {{"segmentation": {{...}}}} 형태로만 출력하십시오.

검색 결과:
{json.dumps(search_results, ensure_ascii=False)}

추가 컨텍스트:
{extra_context or "N/A"}
""".strip()


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _coerce(value: Any, allowed: list[str], default: str) -> str:
    if isinstance(value, str):
        candidate = value.strip()
        if candidate in allowed:
            return candidate
        # Models occasionally answer with the label instead of the id.
        lowered = candidate.lower().replace(" ", "_").replace("-", "_")
        if lowered in allowed:
            return lowered
    return default


def validate_segmentation(raw: Any, taxonomy: dict) -> dict:
    """Normalise a model-produced segmentation against the taxonomy.

    Never raises for bad content: an unusable answer becomes a low-confidence
    `unknown` record so one odd firm cannot abort a long batch run.
    """
    data = raw if isinstance(raw, dict) else {}
    if "segmentation" in data and isinstance(data["segmentation"], dict):
        data = data["segmentation"]

    sectors = sector_ids(taxonomy)
    sector = _coerce(data.get("sector"), sectors, "")
    if not sector:
        # A valid subsector still tells us the sector.
        for candidate in sectors:
            if _coerce(data.get("subsector"), subsector_ids(taxonomy, candidate), ""):
                sector = candidate
                break
    if not sector:
        sector = FALLBACK_SECTOR if FALLBACK_SECTOR in sectors else sectors[-1]

    allowed_subs = subsector_ids(taxonomy, sector)
    subsector = _coerce(data.get("subsector"), allowed_subs, "")
    if not subsector and FALLBACK_SUBSECTOR in allowed_subs:
        subsector = FALLBACK_SUBSECTOR

    vertical_allowed = _ids(taxonomy["verticals"])
    raw_verticals = data.get("verticals")
    if isinstance(raw_verticals, str):
        raw_verticals = [raw_verticals]
    verticals: list[str] = []
    for item in raw_verticals or []:
        coerced = _coerce(item, vertical_allowed, "")
        if coerced and coerced != "none" and coerced not in verticals:
            verticals.append(coerced)
    verticals = verticals[: int(taxonomy.get("max_verticals", 3))]

    levels = taxonomy.get("confidence_levels") or ["high", "medium", "low"]
    raw_confidence = data.get("confidence")
    if isinstance(raw_confidence, str):
        raw_confidence = {axis: raw_confidence for axis in
                          ("sector", "verticals", "business_model", "value_chain", "profile")}
    confidence = {
        axis: _coerce((raw_confidence or {}).get(axis), levels, "low")
        for axis in ("sector", "verticals", "business_model", "value_chain", "profile")
    }

    raw_evidence = data.get("evidence")
    if isinstance(raw_evidence, str):
        evidence = {"overall": raw_evidence.strip()}
    elif isinstance(raw_evidence, dict):
        evidence = {
            str(key): str(value).strip()
            for key, value in raw_evidence.items()
            if value not in (None, "")
        }
    else:
        evidence = {}

    raw_signals = data.get("signals")
    if isinstance(raw_signals, str):
        raw_signals = [raw_signals]
    signals = [str(item).strip() for item in (raw_signals or []) if str(item).strip()][:8]

    raw_profile = data.get("profile") if isinstance(data.get("profile"), dict) else {}

    return {
        "sector": sector,
        "subsector": subsector or None,
        "verticals": verticals,
        "business_model": _coerce(
            data.get("business_model"), _ids(taxonomy["business_models"]), UNKNOWN
        ),
        "value_chain": _coerce(
            data.get("value_chain"), _ids(taxonomy["value_chain"]), UNKNOWN
        ),
        "profile": {
            field: _coerce(raw_profile.get(field), profile_ids(taxonomy, field), UNKNOWN)
            for field in ("size_tier", "rnd_intensity", "research_role")
        },
        "confidence": confidence,
        "evidence": evidence,
        "signals": signals,
    }


def legacy_category(segmentation: dict, taxonomy: dict, valid_ids: Optional[set] = None) -> str:
    """Map a sector onto the coarse `categories` list in config.yml.

    Output directories and the existing dashboard are keyed by those coarse
    ids, so every segmented firm still needs one. `legacy_category` in
    taxonomy.yml carries the mapping.
    """
    sector = segmentation.get("sector")
    mapped = "general"
    for entry in taxonomy["sectors"]:
        if entry.get("id") == sector:
            mapped = entry.get("legacy_category") or "general"
            break

    if valid_ids and mapped not in valid_ids:
        # The config's category list was customised and no longer contains the
        # mapped id; fall back to something that exists so the firm still lands
        # in a real output directory.
        return "general" if "general" in valid_ids else sorted(valid_ids)[0]
    return mapped


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def segmentation_markdown(segmentation: dict, taxonomy: dict) -> str:
    """Render the segmentation as a Markdown block for summary.md."""
    name = labels(taxonomy)

    def label(axis: str, value: Optional[str]) -> str:
        if not value:
            return "-"
        return f"{name[axis].get(value, value)} (`{value}`)"

    verticals = segmentation.get("verticals") or []
    vertical_text = (
        ", ".join(label("vertical", item) for item in verticals) if verticals else "-"
    )
    confidence = segmentation.get("confidence") or {}
    profile = segmentation.get("profile") or {}

    lines = [
        "## 세분류 (Segmentation)",
        "",
        "| 축 | 값 | 확신도 |",
        "| --- | --- | --- |",
        f"| 산업 섹터 | {label('sector', segmentation.get('sector'))} | {confidence.get('sector', '-')} |",
        f"| 세부섹터 | {label('subsector', segmentation.get('subsector'))} | {confidence.get('sector', '-')} |",
        f"| 기술 버티컬 | {vertical_text} | {confidence.get('verticals', '-')} |",
        f"| 사업모델 | {label('business_model', segmentation.get('business_model'))} | {confidence.get('business_model', '-')} |",
        f"| 밸류체인 | {label('value_chain', segmentation.get('value_chain'))} | {confidence.get('value_chain', '-')} |",
        f"| 기업규모 | {label('size_tier', profile.get('size_tier'))} | {confidence.get('profile', '-')} |",
        f"| 연구개발 집약도 | {label('rnd_intensity', profile.get('rnd_intensity'))} | {confidence.get('profile', '-')} |",
        f"| 연구요원 직무 성격 | {label('research_role', profile.get('research_role'))} | {confidence.get('profile', '-')} |",
    ]

    signals = segmentation.get("signals") or []
    if signals:
        lines += ["", f"**분류 신호:** {', '.join(signals)}"]

    evidence = segmentation.get("evidence") or {}
    if evidence:
        lines += ["", "**근거**"]
        for axis, text in evidence.items():
            lines.append(f"- {axis}: {text}")

    return "\n".join(lines)


def segmentation_columns(segmentation: dict) -> dict:
    """Flatten a segmentation into CSV/Supabase-friendly scalar columns."""
    profile = segmentation.get("profile") or {}
    confidence = segmentation.get("confidence") or {}
    return {
        "sector": segmentation.get("sector", ""),
        "subsector": segmentation.get("subsector") or "",
        "verticals": "|".join(segmentation.get("verticals") or []),
        "business_model": segmentation.get("business_model", ""),
        "value_chain": segmentation.get("value_chain", ""),
        "size_tier": profile.get("size_tier", ""),
        "rnd_intensity": profile.get("rnd_intensity", ""),
        "research_role": profile.get("research_role", ""),
        "sector_confidence": confidence.get("sector", ""),
        "signals": "|".join(segmentation.get("signals") or []),
    }
