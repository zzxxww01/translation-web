"""Chatbot 联网回答走官方 Gemini：带 Google 搜索工具，来源取自 grounding_metadata（假的 SDK 客户端）。"""
from types import SimpleNamespace

import pytest

from src.llm.gemini import GeminiProvider


def make_provider(monkeypatch, respond):
    provider = GeminiProvider(api_key="test-not-a-secret", model="gemini-3.8-flash")
    calls = []

    def generate_content(model, contents, config):
        calls.append({"model": model, "contents": contents, "config": config})
        return respond()

    client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
    monkeypatch.setattr(provider, "_use_rest_transport", lambda: False)
    monkeypatch.setattr(provider, "_get_client", lambda key: client)
    return provider, calls


def test_google_search_tool_and_sources(monkeypatch):
    chunks = [SimpleNamespace(web=SimpleNamespace(title="cnn.com", uri="https://example.com/r1")),
              SimpleNamespace(web=None)]
    resp = SimpleNamespace(text=" 新闻 ", usage_metadata=None,
                           candidates=[SimpleNamespace(grounding_metadata=SimpleNamespace(grounding_chunks=chunks))])
    provider, calls = make_provider(monkeypatch, lambda: resp)
    assert provider.generate_with_web_search("有什么新闻", model="gemini-3.8-flash", timeout=30) == {
        "text": "新闻", "sources": [{"title": "cnn.com", "url": "https://example.com/r1"}]}
    assert calls[0]["model"] == "gemini-3.8-flash"
    assert calls[0]["config"]["tools"] == [{"google_search": {}}]


def test_empty_answer_is_an_error(monkeypatch):
    provider, _ = make_provider(monkeypatch, lambda: SimpleNamespace(text="", candidates=[], usage_metadata=None))
    with pytest.raises(Exception):
        provider.generate_with_web_search("hi", timeout=30)
