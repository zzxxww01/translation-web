"""agent 目录：页面上的「通用 Agent + 各专职 Agent（翻译、字幕、播客……）」。

一个 skill 就是一个 agent。名片（中文名、图标、说明、输入提示、示例、默认模型）写在 agents.json，
`skill` 为空串的那条是通用 Agent（直接对话、不派发 skill）。哪些 skill 启用仍由 SKILL_RUNNER_SKILLS 决定，
没写名片的 skill 回退到 skill 名和 SKILL.md 里的简介。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .config import HARNESSES, Config
from .store import iter_skill_catalog

logger = logging.getLogger(__name__)

CHAT_DEFAULT: dict[str, Any] = {
    "title": "通用 Agent",
    "icon": "general",
    "description": "什么都能问，也能在服务器上动手干活",
    "hint": "想问什么、要做什么都可以，也可以附文件或贴链接",
    "examples": [],
}


def load_cards(path: Path) -> dict[str, dict[str, Any]]:
    """按 skill 名索引的名片。文件缺失或写坏了只记日志，页面照样能用（回退到默认名片）。"""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.warning("读不了 agent 名片 %s：%s", path, exc)
        return {}
    cards: dict[str, dict[str, Any]] = {}
    for item in raw if isinstance(raw, list) else []:
        if isinstance(item, dict) and isinstance(item.get("skill"), str):
            cards[item["skill"]] = item
    return cards


def _card(name: str, card: dict[str, Any], fallback: dict[str, Any], available: bool) -> dict[str, Any]:
    examples = card.get("examples", fallback.get("examples", []))
    return {
        "name": name,
        "title": str(card.get("title") or fallback["title"]),
        "icon": str(card.get("icon") or fallback["icon"]),
        "description": str(card.get("description") or fallback.get("description", "")),
        "hint": str(card.get("hint") or fallback.get("hint", "")),
        "examples": [str(e) for e in examples if isinstance(e, str)] if isinstance(examples, list) else [],
        # 新对话默认用哪个模型跑（比如翻译默认 Codex：Claude 不肯全文翻付费文章）；页面上可以改
        "harness": card.get("harness") if card.get("harness") in HARNESSES else "claude",
        "available": available,
    }


def build_catalog(config: Config) -> list[dict[str, Any]]:
    """通用 Agent 在第一位，后面按 SKILL_RUNNER_SKILLS 的顺序列出各 skill。"""
    cards = load_cards(config.agents_file)
    catalog = [_card("", cards.get("", {}), CHAT_DEFAULT, True)]
    for skill in iter_skill_catalog(config.skills_dir, config.skills):
        fallback = {"title": skill["name"], "icon": "skill", "description": skill["description"], "hint": ""}
        catalog.append(_card(skill["name"], cards.get(skill["name"], {}), fallback, skill["available"]))
    return catalog


def prompt_note(catalog: list[dict[str, Any]], skill: str) -> str:
    """按对话追加给 Claude / Codex 的说明。通用 Agent 要知道还有哪些专职 Agent，碰到它们的活就转介。"""
    if skill:
        return ""
    others = [a for a in catalog if a["name"] and a["available"]]
    if not others:
        return ""
    listing = "、".join(f"{a['title']}（{a['name']}）" for a in others)
    return (
        f"- 这是和通用 Agent 的对话。页面上另有专职 Agent，各管一件事：{listing}。"
        "用户要做的正好是其中某个的活时，请用户点「新对话」选对应的 Agent 来做，不要自己调用这些 skill。\n"
    )
