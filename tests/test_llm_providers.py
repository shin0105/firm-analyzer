#!/usr/bin/env python3
"""Tests for provider selection, model resolution and JSON extraction.

No network and no API keys: everything here is about the wiring that decides
which provider and model a run will use, plus the response parsing that has to
tolerate each vendor's idea of "JSON only".
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from firm_analyzer.llm import (  # noqa: E402
    PROVIDER_IDS,
    LLMError,
    describe_providers,
    get_provider,
    resolve_provider_id,
)
from firm_analyzer.llm.providers import (  # noqa: E402
    ClaudeProvider,
    GeminiProvider,
    GitHubModelsProvider,
    OpenAIProvider,
    extract_json,
    retry_transient,
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Provider choice must come from the test, not the developer's .env."""
    for var in ("LLM_PROVIDER", "OPENAI_MODEL", "CLAUDE_MODEL", "GEMINI_MODEL",
                "OPENAI_PARSER_MODEL", "CLAUDE_PARSER_MODEL", "GEMINI_PARSER_MODEL"):
        monkeypatch.delenv(var, raising=False)


def test_every_provider_id_is_constructible():
    for provider_id in PROVIDER_IDS:
        provider = get_provider(provider_id)
        assert provider.id == provider_id
        assert provider.model
        assert provider.parser_model


def test_expected_provider_ids():
    assert set(PROVIDER_IDS) == {"openai", "claude", "gemini", "github"}


def test_implementation_classes():
    assert isinstance(get_provider("openai"), OpenAIProvider)
    assert isinstance(get_provider("claude"), ClaudeProvider)
    assert isinstance(get_provider("gemini"), GeminiProvider)
    assert isinstance(get_provider("github"), GitHubModelsProvider)


def test_precedence_explicit_beats_env_and_config(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    config = {"app": {"llm_provider": "github"}}
    assert resolve_provider_id("claude", config) == "claude"


def test_precedence_env_beats_config(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    assert resolve_provider_id(None, {"app": {"llm_provider": "github"}}) == "gemini"


def test_precedence_config_beats_default():
    assert resolve_provider_id(None, {"app": {"llm_provider": "claude"}}) == "claude"


def test_default_is_openai():
    assert resolve_provider_id(None, {}) == "openai"


def test_vendor_aliases_are_accepted():
    assert resolve_provider_id("anthropic") == "claude"
    assert resolve_provider_id("google") == "gemini"
    assert resolve_provider_id("GEMINI") == "gemini"


def test_unknown_explicit_provider_raises():
    with pytest.raises(LLMError, match="Unknown LLM provider"):
        resolve_provider_id("llama")


def test_unknown_env_or_config_value_falls_back_rather_than_raising(monkeypatch):
    """A typo in the environment must not take the whole pipeline down."""
    monkeypatch.setenv("LLM_PROVIDER", "not-a-provider")
    assert resolve_provider_id(None, {}) == "openai"


def test_model_precedence(monkeypatch):
    config = {"app": {"llm_models": {"openai": "from-config"}}}
    assert get_provider("openai", config=config).model == "from-config"

    monkeypatch.setenv("OPENAI_MODEL", "from-env")
    assert get_provider("openai", config=config).model == "from-env"
    assert get_provider("openai", config=config, model="from-arg").model == "from-arg"


def test_empty_config_model_falls_back_to_default():
    """config.yml ships the keys blank; blank must mean "use the default"."""
    config = {"app": {"llm_models": {"openai": ""}}}
    assert get_provider("openai", config=config).model == "gpt-5"


def test_parser_model_is_resolved_separately(monkeypatch):
    monkeypatch.setenv("GEMINI_PARSER_MODEL", "gemini-parser")
    provider = get_provider("gemini")
    assert provider.parser_model == "gemini-parser"
    assert provider.model == "gemini-3.1-flash-lite"


def test_missing_key_raises_before_any_request(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_API_KEY", raising=False)
    with pytest.raises(LLMError, match="ANTHROPIC_API_KEY"):
        get_provider("claude").api_key()


def test_describe_providers_reports_configuration(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_API_KEY", raising=False)

    rows = {row["id"]: row for row in describe_providers({"app": {"llm_provider": "openai"}})}
    assert rows["openai"]["configured"] is True
    assert rows["openai"]["active"] is True
    assert rows["claude"]["configured"] is False
    # Keys must never be echoed back to a client.
    assert "sk-test" not in str(rows)


def test_native_pdf_support_flags():
    rows = {row["id"]: row for row in describe_providers({})}
    assert rows["claude"]["supports_native_pdf"] is True
    assert rows["gemini"]["supports_native_pdf"] is True
    assert rows["openai"]["supports_native_pdf"] is False


# --- JSON extraction -------------------------------------------------------

def test_extract_plain_json():
    assert extract_json('{"a": 1}') == {"a": 1}


def test_extract_fenced_json():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('```\n[1, 2]\n```') == [1, 2]


def test_extract_json_with_surrounding_prose():
    assert extract_json('Sure! Here is the result:\n{"a": [1, 2]}\nHope that helps.') == {"a": [1, 2]}


def test_extract_json_array():
    assert extract_json('[{"업체명": "테스트"}]') == [{"업체명": "테스트"}]


def test_extract_json_rejects_garbage():
    with pytest.raises(LLMError, match="Could not parse JSON"):
        extract_json("no json here at all")


def test_extract_json_rejects_empty():
    with pytest.raises(LLMError, match="empty"):
        extract_json("   ")


def test_extract_json_tolerates_a_stray_trailing_brace():
    """Observed live: a correct object followed by one extra closing brace."""
    text = '{\n  "url": "https://kias.re.kr",\n  "confidence": "high"\n}\n}'
    assert extract_json(text) == {"url": "https://kias.re.kr", "confidence": "high"}


def test_extract_json_tolerates_trailing_commentary():
    assert extract_json('{"a": 1}\nLet me know if you need more detail.') == {"a": 1}


# --- Transient-error retries ----------------------------------------------

def test_transient_error_is_retried(monkeypatch):
    monkeypatch.setattr("firm_analyzer.llm.providers.time.sleep", lambda _: None)
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise RuntimeError("503 UNAVAILABLE: model is experiencing high demand")
        return "ok"

    assert retry_transient(flaky) == "ok"
    assert len(calls) == 3


def test_spent_quota_is_not_retried(monkeypatch):
    """Backing off cannot refill a quota, so fail fast with the real message."""
    monkeypatch.setattr("firm_analyzer.llm.providers.time.sleep", lambda _: None)
    calls = []

    def broke():
        calls.append(1)
        raise RuntimeError("Error code: 429 - insufficient_quota: exceeded your current quota")

    with pytest.raises(RuntimeError, match="insufficient_quota"):
        retry_transient(broke)
    assert len(calls) == 1


def test_unrelated_error_is_not_retried(monkeypatch):
    monkeypatch.setattr("firm_analyzer.llm.providers.time.sleep", lambda _: None)
    calls = []

    def broke():
        calls.append(1)
        raise ValueError("malformed request")

    with pytest.raises(ValueError):
        retry_transient(broke)
    assert len(calls) == 1


def test_exhausted_retries_raise_llm_error(monkeypatch):
    monkeypatch.setattr("firm_analyzer.llm.providers.time.sleep", lambda _: None)

    def always_busy():
        raise RuntimeError("429 rate limit exceeded")

    with pytest.raises(LLMError, match="still unavailable after 3 attempts"):
        retry_transient(always_busy)
