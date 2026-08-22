#!/usr/bin/env python3
"""Tests for taxonomy loading, prompt assembly and segmentation validation.

The validation tests matter most: they are what stops a model's invented label
from reaching a CSV column or a Supabase row.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from firm_analyzer.core import segmentation as seg  # noqa: E402


@pytest.fixture(scope="module")
def taxonomy():
    return seg.load_taxonomy()


def test_taxonomy_loads_with_all_axes(taxonomy):
    for axis in ("sectors", "verticals", "business_models", "value_chain", "profile"):
        assert taxonomy[axis]


def test_sector_ids_are_unique(taxonomy):
    ids = seg.sector_ids(taxonomy)
    assert len(ids) == len(set(ids))
    assert "ict_software" in ids
    assert "semiconductor_hardware" in ids


def test_subsector_ids_are_globally_unique(taxonomy):
    """Subsector ids double as labels in flat CSV columns, so they must not collide."""
    seen = []
    for sector in taxonomy["sectors"]:
        for sub in sector.get("subsectors") or []:
            seen.append(sub["id"])
    assert len(seen) == len(set(seen)), "duplicate subsector id in taxonomy.yml"


def test_every_sector_maps_to_a_legacy_category(taxonomy):
    for sector in taxonomy["sectors"]:
        assert sector.get("legacy_category"), f"{sector['id']} has no legacy_category"


def test_digest_includes_ids_keywords_and_rules(taxonomy):
    digest = seg.taxonomy_digest(taxonomy)
    assert "ict_software" in digest
    assert "fabless_design" in digest
    assert "구분기준" in digest       # per-sector tie-breaks
    assert "주된 산업활동" in digest  # global KSIC rule


def test_prompt_contains_the_firm_and_the_contract(taxonomy):
    prompt = seg.build_segmentation_prompt(
        "테스트반도체", [{"title": "팹리스 기업", "url": "https://example.com"}], taxonomy
    )
    assert "테스트반도체" in prompt
    assert '"segmentation"' in prompt
    assert "example.com" in prompt


# --- Validation ------------------------------------------------------------

def test_valid_payload_passes_through(taxonomy):
    result = seg.validate_segmentation(
        {
            "sector": "semiconductor_hardware",
            "subsector": "fabless_design",
            "verticals": ["chip_design", "ai_ml"],
            "business_model": "component_supplier",
            "value_chain": "parts",
            "profile": {"size_tier": "startup", "rnd_intensity": "high", "research_role": "applied_dev"},
            "confidence": {"sector": "high", "verticals": "medium"},
            "evidence": {"sector": "NPU 설계 IP를 라이선스한다."},
            "signals": ["팹리스", "NPU"],
        },
        taxonomy,
    )
    assert result["sector"] == "semiconductor_hardware"
    assert result["subsector"] == "fabless_design"
    assert result["verticals"] == ["chip_design", "ai_ml"]
    assert result["profile"]["rnd_intensity"] == "high"
    assert result["confidence"]["sector"] == "high"
    # Axes the model left out default to low rather than being dropped.
    assert result["confidence"]["business_model"] == "low"


def test_wrapped_payload_is_unwrapped(taxonomy):
    result = seg.validate_segmentation({"segmentation": {"sector": "finance"}}, taxonomy)
    assert result["sector"] == "finance"


def test_invented_labels_are_replaced(taxonomy):
    result = seg.validate_segmentation(
        {
            "sector": "quantum_banking",
            "verticals": ["telepathy", "ai_ml"],
            "business_model": "vibes",
            "value_chain": "somewhere",
            "profile": {"size_tier": "huge"},
        },
        taxonomy,
    )
    assert result["sector"] == seg.FALLBACK_SECTOR
    assert result["verticals"] == ["ai_ml"]
    assert result["business_model"] == "unknown"
    assert result["value_chain"] == "unknown"
    assert result["profile"]["size_tier"] == "unknown"


def test_subsector_from_another_sector_is_dropped(taxonomy):
    result = seg.validate_segmentation(
        {"sector": "finance", "subsector": "fabless_design"}, taxonomy
    )
    assert result["sector"] == "finance"
    assert result["subsector"] is None


def test_sector_is_recovered_from_a_valid_subsector(taxonomy):
    result = seg.validate_segmentation({"subsector": "drug_discovery"}, taxonomy)
    assert result["sector"] == "bio_health"
    assert result["subsector"] == "drug_discovery"


def test_verticals_are_capped_and_deduplicated(taxonomy):
    result = seg.validate_segmentation(
        {"sector": "ict_software",
         "verticals": ["ai_ml", "ai_ml", "genai_llm", "nlp_speech", "computer_vision"]},
        taxonomy,
    )
    assert result["verticals"] == ["ai_ml", "genai_llm", "nlp_speech"]


def test_none_vertical_is_stripped(taxonomy):
    result = seg.validate_segmentation(
        {"sector": "ict_software", "verticals": ["none"]}, taxonomy
    )
    assert result["verticals"] == []


def test_scalar_shapes_are_accepted(taxonomy):
    """Models sometimes answer with a string where the contract says object/list."""
    result = seg.validate_segmentation(
        {"sector": "finance", "verticals": "ai_ml", "confidence": "high",
         "evidence": "자산운용 매출이 대부분이다.", "signals": "퀀트"},
        taxonomy,
    )
    assert result["verticals"] == ["ai_ml"]
    assert result["confidence"]["sector"] == "high"
    assert result["evidence"] == {"overall": "자산운용 매출이 대부분이다."}
    assert result["signals"] == ["퀀트"]


def test_junk_input_degrades_instead_of_raising(taxonomy):
    for junk in (None, "nope", [], 42):
        result = seg.validate_segmentation(junk, taxonomy)
        assert result["sector"] in seg.sector_ids(taxonomy)
        assert result["confidence"]["sector"] == "low"


# --- Mapping and rendering -------------------------------------------------

def test_legacy_category_mapping(taxonomy):
    valid = {"finance", "healthcare", "ai_ml", "general"}
    assert seg.legacy_category({"sector": "finance"}, taxonomy, valid) == "finance"
    assert seg.legacy_category({"sector": "bio_health"}, taxonomy, valid) == "healthcare"
    assert seg.legacy_category({"sector": "ict_software"}, taxonomy, valid) == "ai_ml"
    assert seg.legacy_category({"sector": "chem_materials_energy"}, taxonomy, valid) == "general"


def test_legacy_category_respects_a_customised_category_list(taxonomy):
    """A config that dropped `general` must still get a directory that exists."""
    assert seg.legacy_category({"sector": "ict_software"}, taxonomy, {"finance"}) == "finance"


def test_markdown_renders_korean_labels(taxonomy):
    segmentation = seg.validate_segmentation(
        {"sector": "semiconductor_hardware", "subsector": "fabless_design",
         "verticals": ["chip_design"], "business_model": "component_supplier",
         "value_chain": "parts", "signals": ["팹리스"],
         "evidence": {"sector": "설계 전문"}},
        taxonomy,
    )
    markdown = seg.segmentation_markdown(segmentation, taxonomy)
    assert "반도체·전자부품" in markdown
    assert "반도체 설계(팹리스)" in markdown
    assert "`fabless_design`" in markdown
    assert "팹리스" in markdown
    assert "설계 전문" in markdown


def test_columns_are_flat_scalars(taxonomy):
    segmentation = seg.validate_segmentation(
        {"sector": "ict_software", "verticals": ["ai_ml", "genai_llm"]}, taxonomy
    )
    columns = seg.segmentation_columns(segmentation)
    assert columns["verticals"] == "ai_ml|genai_llm"
    assert all(isinstance(value, str) for value in columns.values())
