"""
Slack 页的轻量 AI：消息配中文、thread 摘要、我的待办、帖子提取。

和 skill agent 不同，这些直接调短文本模型（task_type="slack"），提示词在 src/prompts/slack_*.txt。
结果按内容 hash 缓存到 data/slack_cache/ai/*.json，同一段内容只付一次钱。这里只放渲染、解析和缓存
（纯函数，好测）；真正的模型调用由路由层注入。
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence

from src.prompts import get_prompt_manager

logger = logging.getLogger(__name__)

# 一次请求最多带多少条；前端按批次请求
MAX_BATCH = 40
MAX_TEXT_CHARS = 4000
MAX_CONTEXT_CHARS = 2000
# 每类缓存最多保留多少条，超出删最旧的一批
CACHE_LIMIT = 20000
# 改了提示词或换了模型就改这个标记，旧缓存自然失效
# sol1：2026-11-17 起官方 GPT-6.1 Sol；sol2：2026-11-22 升 6.2、提示词挪到 src/prompts 并重写
CACHE_TAG = "sol2"
ZH_PROMPT_VERSION = f"zh3-{CACHE_TAG}"
TODO_MAX_ITEMS = 20

_URL_RE = re.compile(r"https?://\S+")
_MENTION_RE = re.compile(r"[@#][\w.\-()（）一-鿿]+")
_EMOJI_CODE_RE = re.compile(r":[a-z0-9_+\-]+:")
_CJK_RE = re.compile(r"[一-鿿]")
_LATIN_WORD_RE = re.compile(r"[A-Za-z]{2,}")
TODO_ACTIONS = ("reply", "do", "read")

LLM = Callable[[str], Awaitable[str]]


def text_key(*parts: str) -> str:
    return hashlib.sha1("\x1f".join(parts).encode("utf-8")).hexdigest()


def needs_translation(text: str) -> bool:
    """只翻英文为主的消息：去掉链接、@提及、表情码后，至少有两个英文词，且中文占比不高。"""
    core = _EMOJI_CODE_RE.sub(" ", _MENTION_RE.sub(" ", _URL_RE.sub(" ", text or "")))
    words = _LATIN_WORD_RE.findall(core)
    if len(words) < 2:
        return False
    cjk = len(_CJK_RE.findall(core))
    letters = sum(len(w) for w in words)
    return cjk < letters * 0.3


class JsonCache:
    """一个 JSON 文件当缓存：key -> value。进程内加锁，原子写。"""

    def __init__(self, path: Path, limit: int = CACHE_LIMIT):
        self.path = Path(path)
        self.limit = limit
        self._lock = threading.Lock()
        self._data: Dict[str, Any] = {}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                self._data = raw
        except (OSError, ValueError):
            pass

    def get(self, key: str) -> Any:
        return self._data.get(key)

    def put_many(self, items: Dict[str, Any]) -> None:
        if not items:
            return
        with self._lock:
            self._data.update(items)
            if len(self._data) > self.limit:
                # dict 保持插入顺序：删最早写入的
                for k in list(self._data)[: len(self._data) - self.limit]:
                    self._data.pop(k, None)
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                tmp = self.path.with_suffix(".tmp")
                tmp.write_text(json.dumps(self._data, ensure_ascii=False), encoding="utf-8")
                os.replace(tmp, self.path)
            except OSError:
                logger.warning("写 Slack AI 缓存失败: %s", self.path, exc_info=True)


# ---------------------------------------------------------------- 提示词（模板在 src/prompts/slack_*.txt）

def translate_prompt(texts: Sequence[str], glossary: str, context: Optional[str] = None) -> str:
    items = [{"id": i, "text": t[:MAX_TEXT_CHARS]} for i, t in enumerate(texts)]
    context_section = ""
    if context and context.strip():
        context_section = (
            "\n## 背景：这些消息所在 thread 的根帖（只用来理解，不要翻译它）\n"
            + context.strip()[:MAX_CONTEXT_CHARS] + "\n"
        )
    return get_prompt_manager().render(
        "slack_zh",
        context_section=context_section,
        glossary=glossary.strip(),
        items_json=json.dumps({"items": items}, ensure_ascii=False),
    )


def summary_prompt(thread_markdown: str) -> str:
    return get_prompt_manager().render("slack_summary", thread=thread_markdown[:24000])


def todo_prompt(items: Sequence[Dict[str, Any]]) -> str:
    return get_prompt_manager().render("slack_todo", items_json=json.dumps({"items": list(items)}, ensure_ascii=False))


def extract_prompt(thread: Sequence[Dict[str, Any]], instruction: Optional[str] = None) -> str:
    section = ""
    if instruction and instruction.strip():
        section = f"\n## 用户这次的要求（优先满足）\n{instruction.strip()[:500]}\n"
    return get_prompt_manager().render(
        "slack_post_extract",
        instruction_section=section,
        thread_json=json.dumps(list(thread), ensure_ascii=False),
    )


# ---------------------------------------------------------------- 解析

def parse_items(data: Any, field: str, count: int) -> List[Optional[str]]:
    out: List[Optional[str]] = [None] * count
    items = data.get("items") if isinstance(data, dict) else None
    for item in items or []:
        if not isinstance(item, dict):
            continue
        try:
            idx = int(item.get("id"))
        except (TypeError, ValueError):
            continue
        value = item.get(field)
        if 0 <= idx < count and isinstance(value, str) and value.strip():
            out[idx] = value.strip()
    return out


def _ints(values: Any) -> List[int]:
    out = []
    for v in values if isinstance(values, list) else []:
        try:
            out.append(int(v))
        except (TypeError, ValueError):
            continue
    return out


def _image_ids(values: Any, allowed: Sequence[str]) -> List[str]:
    """模型给的图片 ID 只保留输入里真有的，去重保序。"""
    allowed_set = set(allowed)
    out: List[str] = []
    for v in values if isinstance(values, list) else []:
        if isinstance(v, str) and v in allowed_set and v not in out:
            out.append(v)
    return out


def parse_extraction(data: Any, allowed_images: Sequence[str]) -> Dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("提取结果不是 JSON 对象")
    source = str(data.get("source_text") or "").strip()
    images = _image_ids(data.get("image_ids"), allowed_images)
    has_post = bool(data.get("has_post", True)) and bool(source or images)
    candidates = []
    for c in data.get("candidates") or []:
        if isinstance(c, dict) and str(c.get("source_text") or "").strip():
            candidates.append({
                "label": str(c.get("label") or "").strip()[:200],
                "source_text": str(c["source_text"]).strip(),
                "message_ids": _ints(c.get("message_ids")),
                "image_ids": _image_ids(c.get("image_ids"), allowed_images),
            })
    note = str(data.get("note") or "").strip()[:500]
    if not has_post and not note:
        raise ValueError("模型没有给出提取结果")
    send_time = data.get("send_time")
    send_id = _ints([send_time.get("message_id")]) if isinstance(send_time, dict) else []
    return {
        "send_time": {**send_time, "message_id": send_id[0] if send_id else None}
        if has_post and isinstance(send_time, dict) and send_time.get("date") else None,
        "has_post": has_post,
        "source_text": source if has_post else "",
        "note": note,
        "message_ids": _ints(data.get("message_ids")),
        "image_ids": images if has_post else [],
        "candidates": candidates[:2],
    }


# ---------------------------------------------------------------- 服务

class SlackAI:
    def __init__(self, cache_dir: Path, llm: LLM, parse: Callable[[str], Dict[str, Any]],
                 glossary: Callable[[str], Awaitable[str]]):
        self.zh = JsonCache(Path(cache_dir) / "zh.json")
        self.summaries = JsonCache(Path(cache_dir) / "summaries.json", limit=5000)
        self.todos = JsonCache(Path(cache_dir) / "todos.json", limit=500)
        self._llm = llm
        self._parse = parse
        self._glossary = glossary

    async def translate(self, texts: Sequence[str], context: Optional[str] = None) -> List[Optional[str]]:
        """逐条返回中文；不需要翻的（中文、只有链接/表情）返回 None。只把没缓存的送去模型。

        context：thread 根帖，只帮模型理解指代；它也进缓存键（同一句话在不同 thread 里可能翻得不同）。
        """
        texts = list(texts)[:MAX_BATCH]
        ctx_key = text_key(context.strip()[:MAX_CONTEXT_CHARS]) if context and context.strip() else ""
        result: List[Optional[str]] = [None] * len(texts)
        todo: Dict[str, str] = {}
        for i, text in enumerate(texts):
            if not needs_translation(text):
                continue
            key = text_key(ZH_PROMPT_VERSION, ctx_key, text)
            cached = self.zh.get(key)
            if cached:
                result[i] = cached
            else:
                todo.setdefault(key, text)
        if todo:
            keys, sources = list(todo), list(todo.values())
            glossary = await self._glossary("\n".join(sources))
            data = self._parse(await self._llm(translate_prompt(sources, glossary, context)))
            translated = parse_items(data, "zh", len(sources))
            self.zh.put_many({k: zh for k, zh in zip(keys, translated) if zh})
            for i, text in enumerate(texts):
                if result[i] is None and needs_translation(text):
                    result[i] = self.zh.get(text_key(ZH_PROMPT_VERSION, ctx_key, text))
        return result

    async def summary(self, cache_key: str, thread_markdown: str) -> Dict[str, str]:
        """thread 摘要；cache_key 里带上最新回复的 ts，有新回复就重算。"""
        cache_key = f"{CACHE_TAG}:{cache_key}"
        cached = self.summaries.get(cache_key)
        if cached:
            return cached
        data = self._parse(await self._llm(summary_prompt(thread_markdown)))
        result = {
            "summary": str(data.get("summary") or "").strip(),
            "todo_for_me": str(data.get("todo_for_me") or "").strip(),
        }
        if not result["summary"]:
            raise ValueError("模型没有给出摘要")
        self.summaries.put_many({cache_key: result})
        return result

    async def todo_tasks(self, items: Sequence[Dict[str, Any]]) -> List[Dict[str, str]]:
        """我的待办：每项一句「谁要我干什么」+ action。整批一次调用，按这批消息缓存。"""
        items = list(items)[:TODO_MAX_ITEMS]
        if not items:
            return []
        cache_key = text_key(CACHE_TAG, json.dumps(items, ensure_ascii=False, sort_keys=True))
        cached = self.todos.get(cache_key)
        if cached:
            return cached
        data = self._parse(await self._llm(todo_prompt(items)))
        tasks = parse_items(data, "task", len(items))
        actions = parse_items(data, "action", len(items))
        out = [
            {"task": task or "", "action": action if action in TODO_ACTIONS else "read"}
            for task, action in zip(tasks, actions)
        ]
        if not any(o["task"] for o in out):
            raise ValueError("模型没有给出待办")
        self.todos.put_many({cache_key: out})
        return out

    async def extract_post(self, thread: Sequence[Dict[str, Any]], allowed_images: Sequence[str],
                           instruction: Optional[str] = None) -> Dict[str, Any]:
        """从整个 thread 里提取要发的那一篇帖子原文和配图（不缓存：每次都是用户主动要的）。"""
        data = self._parse(await self._llm(extract_prompt(thread, instruction)))
        return parse_extraction(data, allowed_images)
