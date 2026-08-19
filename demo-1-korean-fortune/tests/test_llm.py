"""Tests for the pluggable LLM provider layer.

Covers provider resolution (env-driven, incl. local-AI mode) and the JSON
extraction helper that tolerates coding-agent CLI wrapping.
"""

from __future__ import annotations

import pytest

from src import llm


@pytest.fixture(autouse=True)
def _clear_provider_env(monkeypatch):
    """Start each test from a clean provider environment."""
    for var in ("FORTUNE_PROVIDER", "OPENAI_API_KEY"):
        monkeypatch.delenv(var, raising=False)


def test_resolve_defaults_to_claude_without_key(monkeypatch):
    # Local-AI mode by default: no key, no explicit provider -> Claude CLI.
    assert llm.resolve_provider() == llm.CLAUDE


def test_resolve_defaults_to_openai_with_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    assert llm.resolve_provider() == llm.OPENAI


def test_explicit_provider_overrides_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("FORTUNE_PROVIDER", "cursor")
    assert llm.resolve_provider() == llm.CURSOR


def test_explicit_provider_case_insensitive(monkeypatch):
    monkeypatch.setenv("FORTUNE_PROVIDER", "  Claude ")
    assert llm.resolve_provider() == llm.CLAUDE


def test_unknown_provider_raises(monkeypatch):
    monkeypatch.setenv("FORTUNE_PROVIDER", "llama")
    with pytest.raises(llm.LLMError):
        llm.resolve_provider()


def test_extract_json_plain():
    data = llm.extract_json('{"a": 1, "b": "x"}')
    assert data == {"a": 1, "b": "x"}


def test_extract_json_with_fences():
    text = '```json\n{"a": 1}\n```'
    assert llm.extract_json(text) == {"a": 1}


def test_extract_json_with_commentary():
    text = 'Sure, here is your fortune:\n{"fortune_message": "hi"}\nHope that helps!'
    assert llm.extract_json(text) == {"fortune_message": "hi"}


def test_extract_json_no_object_raises():
    with pytest.raises(llm.LLMError):
        llm.extract_json("no json here")
