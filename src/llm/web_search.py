"""Chatbot 联网回答：按模型别名找到能联网的官方 provider，用它自带的搜索工具回答。

- 官方 OpenAI：Responses API 的 web_search；官方 Gemini：Google 搜索工具。搜不搜由模型自己决定，
  不需要搜索的问题和普通回答一样快。
- 中转（RelayRouter）的模型没有搜索工具：同一个模型有官方路线就走官方搜，否则返回 None，
  调用方照常不联网回答并告诉用户。
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .config_models import is_relay_provider
from .provider_adapter import get_provider_adapter


def supports_web_search(model_alias: str) -> bool:
    try:
        adapter = get_provider_adapter(model_alias)
    except ValueError:
        return False
    return bool(_search_plans(adapter))


def _search_plans(adapter: Any) -> list:
    """能联网的路线：官方 OpenAI / Gemini，且必须是用户选的同一个模型（中转的 Gemini 3.8 Flash 可以走官方的
    Gemini 3.8 Flash 搜；Qwen 不能为了搜索换成 Gemini 回答）。"""
    plans = adapter._bounded_attempt_plan()
    if not plans:
        return []
    real_model = plans[0].model.real_model
    out = []
    for plan in plans:
        if (not is_relay_provider(plan.provider) and plan.provider.type in ("openai", "gemini")
                and plan.model.real_model == real_model and plan not in out):
            out.append(plan)
    return out


def generate_with_web_search(prompt: str, model_alias: str, timeout: int) -> Optional[Dict[str, Any]]:
    """返回 {"text", "sources"}；这个模型不能联网返回 None。官方路线上换 Key 重试一次，失败抛最后的错。"""
    adapter = get_provider_adapter(model_alias)
    plans = _search_plans(adapter)
    if not plans:
        return None
    last_error: Optional[Exception] = None
    for plan in plans[:2]:
        provider = adapter.create_provider(plan)
        try:
            return provider.generate_with_web_search(prompt, model=plan.model.real_model, timeout=timeout)
        except Exception as exc:  # noqa: BLE001 — 换下一个 Key，都不行再抛
            last_error = exc
    assert last_error is not None
    raise last_error
