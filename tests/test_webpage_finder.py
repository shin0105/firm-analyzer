#!/usr/bin/env python3
"""Structure tests for the firm webpage finder (no network, no API keys)."""

import inspect
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from firm_analyzer.utils.webpage_finder import (  # noqa: E402
    find_firm_webpage,
    initialize_clients,
    verify_firm_webpage,
)


def test_public_functions_exist():
    for fn in (initialize_clients, find_firm_webpage, verify_firm_webpage):
        assert callable(fn)


def test_find_firm_webpage_signature():
    params = list(inspect.signature(find_firm_webpage).parameters)
    assert params[:3] == ["firm_name", "tavily_client", "llm"]


def test_verify_firm_webpage_signature():
    params = list(inspect.signature(verify_firm_webpage).parameters)
    assert params[:3] == ["firm_name", "candidates", "llm"]


def test_verification_uses_the_provider_and_survives_bad_json(monkeypatch):
    """A non-dict LLM answer must return None rather than raising."""

    class StubProvider:
        label = "Stub"
        model = "stub-1"

        def complete_json(self, prompt, system=None, max_output_tokens=None):
            return ["not", "an", "object"]

    assert verify_firm_webpage("테스트", [{"url": "https://example.com"}], StubProvider()) is None


def test_verification_returns_the_selected_url():
    class StubProvider:
        label = "Stub"
        model = "stub-1"

        def complete_json(self, prompt, system=None, max_output_tokens=None):
            assert "테스트" in prompt
            return {"url": "https://example.com", "confidence": "high", "reasoning": "도메인 일치"}

    result = verify_firm_webpage("테스트", [{"url": "https://example.com"}], StubProvider())
    assert result["url"] == "https://example.com"
    assert result["confidence"] == "high"
