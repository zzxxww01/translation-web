"""工具箱 Chatbot 接口，以及模型显示名的供应商标注规则。"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.middleware import register_error_handlers
from src.api.middleware.rate_limit import limiter
from src.api.routers import models as models_router
from src.api.routers import tools as tools_router
from src.api.routers import tools_chat
from src.api.routers.tools_models import ChatMessage


def make_client(monkeypatch, reply="你好！", calls=None):
    async def fake_generate(prompt, *, task_type, model=None, **kwargs):
        if calls is not None:
            calls.append({"prompt": prompt, "task_type": task_type, "model": model})
        return f"  {reply}  "

    monkeypatch.setattr(tools_chat, "generate_with_fallback_budget", fake_generate)
    app = FastAPI()
    app.state.limiter = limiter
    register_error_handlers(app)
    app.include_router(tools_router.router, prefix="/api")
    return TestClient(app)


def test_chat_uses_chat_task_default_and_sends_history(monkeypatch):
    calls = []
    client = make_client(monkeypatch, calls=calls)
    res = client.post("/api/tools/chat", json={"messages": [
        {"role": "user", "content": "HBM 是什么？"},
        {"role": "assistant", "content": "高带宽内存。"},
        {"role": "user", "content": "和 GDDR 比呢？"},
    ]})
    assert res.status_code == 200
    assert res.json() == {"reply": "你好！"}
    call = calls[0]
    assert call["task_type"] == "chat" and call["model"] is None
    # 历史按顺序进入 prompt，最后一条是用户刚发的
    assert call["prompt"].index("HBM 是什么") < call["prompt"].index("高带宽内存") < call["prompt"].index("和 GDDR 比呢")


def test_chat_passes_explicit_model(monkeypatch):
    calls = []
    client = make_client(monkeypatch, calls=calls)
    res = client.post("/api/tools/chat", json={"messages": [{"role": "user", "content": "hi"}], "model": "gemini-flash"})
    assert res.status_code == 200 and calls[0]["model"] == "gemini-flash"


def test_chat_rejects_history_not_ending_with_user(monkeypatch):
    client = make_client(monkeypatch)
    res = client.post("/api/tools/chat", json={"messages": [{"role": "assistant", "content": "hi"}]})
    assert res.status_code in (400, 422)


def test_conversation_keeps_latest_turns_within_budget(monkeypatch):
    monkeypatch.setattr(tools_chat, "MAX_HISTORY_CHARS", 50)
    messages = [ChatMessage(role="user", content="旧" * 40), ChatMessage(role="assistant", content="答"),
                ChatMessage(role="user", content="最新的问题")]
    text = tools_chat.build_conversation(messages)
    assert "最新的问题" in text and "旧旧旧" not in text


def _provider(pid, name, *models):
    return models_router.ProviderInfo(id=pid, name=name, description="", models=[
        models_router.ModelInfo(alias=alias, name=label, description="", supports_thinking=False,
                                priority=1, available=True, real_model=real)
        for alias, real, label in models
    ])


def test_model_names_only_mention_supplier_when_shared():
    providers = [
        _provider("gemini-official", "Gemini 官方 API", ("gemini-flash-fallback", "gemini-3.8-flash", "Gemini 3.8 Flash")),
        _provider("relay", "RelayRouter 中转", ("gemini-flash", "gemini-3.8-flash", "Gemini 3.8 Flash"),
                  ("qwen-plus", "qwen3.6-plus", "Qwen 3.6 Plus")),
        _provider("openai-official", "OpenAI 官方 API", ("gpt-6.2-sol", "gpt-6.2-sol", "GPT-6.2 Sol")),
    ]
    models_router._label_shared_models(providers)
    names = {m.alias: m.name for p in providers for m in p.models}
    assert names["gpt-6.2-sol"] == "GPT-6.2 Sol"
    assert names["qwen-plus"] == "Qwen 3.6 Plus"
    assert names["gemini-flash-fallback"] == "Gemini 3.8 Flash（Gemini 官方）"
    assert names["gemini-flash"] == "Gemini 3.8 Flash（RelayRouter 中转）"
