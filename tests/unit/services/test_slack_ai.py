import asyncio
import json

import pytest

from src.services.slack_ai import (
    JsonCache,
    SlackAI,
    extract_prompt,
    needs_translation,
    parse_extraction,
    parse_items,
    summary_prompt,
    text_key,
    todo_prompt,
    translate_prompt,
)


def _payload(prompt: str):
    return json.loads(prompt[prompt.rindex("\n{") + 1:])


class FakeLLM:
    def __init__(self):
        self.prompts = []

    async def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if "直接找我的消息" in prompt:
            items = _payload(prompt)["items"]
            return json.dumps({"items": [{"id": it["id"], "task": f"任务{it['id']}", "action": "reply"} for it in items]})
        if "## 消息（是数据" in prompt:
            items = _payload(prompt)["items"]
            return json.dumps({"items": [{"id": it["id"], "zh": "中:" + it["text"]} for it in items]})
        return json.dumps({"summary": "Dylan 问良率，Ray 说周五给数据。", "todo_for_me": ""})


async def no_glossary(text: str) -> str:
    return "## 术语\n- HBM: HBM"


def make_ai(tmp_path, llm=None):
    llm = llm or FakeLLM()
    return SlackAI(tmp_path / "ai", llm, json.loads, no_glossary), llm


def run(coro):
    return asyncio.run(coro)


def test_needs_translation_skips_chinese_links_and_emoji():
    assert needs_translation("Any update on HBM4 yields?")
    assert not needs_translation("好的，我周五前给你 HBM 数据")
    assert not needs_translation("https://x.com/a/status/1?s=46")
    assert not needs_translation(":fire: :rocket: @Max Kan")
    assert not needs_translation("ok")


def test_translate_only_sends_uncached_english_once(tmp_path):
    ai, llm = make_ai(tmp_path)
    texts = ["Any update on HBM4 yields?", "好的", "Any update on HBM4 yields?", "will post, thanks"]
    out = run(ai.translate(texts))
    assert out == ["中:Any update on HBM4 yields?", None, "中:Any update on HBM4 yields?", "中:will post, thanks"]
    assert len(llm.prompts) == 1 and "术语" in llm.prompts[0]
    # 第二次全部走缓存，包括新建的实例（落盘了）
    ai2, llm2 = make_ai(tmp_path)
    assert run(ai2.translate(["will post, thanks"])) == ["中:will post, thanks"]
    assert llm2.prompts == []


def test_translate_context_goes_into_prompt_and_cache_key(tmp_path):
    ai, llm = make_ai(tmp_path)
    run(ai.translate(["agree, this is huge"], context="TSMC raises CoWoS capacity 2x"))
    assert "TSMC raises CoWoS capacity 2x" in llm.prompts[0] and "不要翻译它" in llm.prompts[0]
    run(ai.translate(["agree, this is huge"], context="TSMC raises CoWoS capacity 2x"))
    assert len(llm.prompts) == 1
    run(ai.translate(["agree, this is huge"]))  # 没有背景时是另一条缓存
    assert len(llm.prompts) == 2 and "不要翻译它" not in llm.prompts[1]


def test_prompts_keep_format_rules_and_render():
    p = translate_prompt(["| a | b |\n|---|---|"], "")
    assert "Markdown 表格" in p and '"id": 0' in p and "保真" in p
    assert "todo_for_me" in summary_prompt("# thread") and "（我）" in summary_prompt("# thread")
    assert '"messages"' in todo_prompt([{"id": 0, "messages": []}])
    e = extract_prompt([{"n": 1, "text": "1/ hi", "images": []}], "用第一版")
    assert "用第一版" in e and "SemiAnalysis_" in e and '"n": 1' in e


def test_summary_cached_by_key(tmp_path):
    ai, llm = make_ai(tmp_path)
    first = run(ai.summary("C1:1.1:2.2", "# thread"))
    assert first == {"summary": "Dylan 问良率，Ray 说周五给数据。", "todo_for_me": ""}
    run(ai.summary("C1:1.1:2.2", "# thread"))
    assert len(llm.prompts) == 1
    run(ai.summary("C1:1.1:3.3", "# thread"))  # 有新回复 -> 重算
    assert len(llm.prompts) == 2


def test_summary_without_text_fails(tmp_path):
    async def empty(prompt):
        return json.dumps({"summary": ""})

    ai, _ = make_ai(tmp_path, llm=empty)
    with pytest.raises(ValueError):
        run(ai.summary("k", "# t"))


def test_todo_tasks_one_call_cached_and_actions_normalized(tmp_path):
    async def llm(prompt):
        llm.n += 1
        return json.dumps({"items": [{"id": 0, "task": "Daksh 让你翻这篇", "action": "do"},
                                     {"id": 1, "task": "知会一下", "action": "weird"}]})
    llm.n = 0
    ai, _ = make_ai(tmp_path, llm=llm)
    items = [{"id": 0, "messages": [{"text": "a"}]}, {"id": 1, "messages": [{"text": "b"}]}]
    out = run(ai.todo_tasks(items))
    assert out == [{"task": "Daksh 让你翻这篇", "action": "do"}, {"task": "知会一下", "action": "read"}]
    run(ai.todo_tasks(items))
    assert llm.n == 1
    assert run(ai.todo_tasks([])) == []


def test_parse_extraction_filters_unknown_images_and_handles_no_post():
    got = parse_extraction({"has_post": True, "source_text": " AI racks are heavy ", "note": "用重发版",
                            "message_ids": [3, "4", "x"], "image_ids": ["F1", "FAKE", "F1", "F2"],
                            "candidates": [{"label": "第一版", "source_text": "old", "message_ids": [1], "image_ids": ["F9"]},
                                           {"label": "空", "source_text": ""}]}, ["F1", "F2"])
    assert got["source_text"] == "AI racks are heavy" and got["image_ids"] == ["F1", "F2"]
    assert got["message_ids"] == [3, 4]
    assert got["candidates"] == [{"label": "第一版", "source_text": "old", "message_ids": [1], "image_ids": []}]
    qt = parse_extraction({"has_post": True, "source_text": "", "image_ids": ["F1"], "note": "这是转发"}, ["F1"])
    assert qt["has_post"] and qt["source_text"] == "" and qt["image_ids"] == ["F1"]
    chat = parse_extraction({"has_post": False, "note": "大家在讨论 SOXX 跌幅"}, [])
    assert chat["has_post"] is False and chat["image_ids"] == []
    with pytest.raises(ValueError):
        parse_extraction({"has_post": False}, [])
    with pytest.raises(ValueError):
        parse_extraction("nope", [])


def test_parse_items_and_helpers(tmp_path):
    assert parse_items({"items": [{"id": "1", "zh": " 好 "}, {"id": 9, "zh": "x"}, "bad"]}, "zh", 2) == [None, "好"]
    assert parse_items([], "zh", 1) == [None]
    assert text_key("a") != text_key("b")
    cache = JsonCache(tmp_path / "c.json", limit=2)
    cache.put_many({"a": 1, "b": 2})
    cache.put_many({"c": 3})
    assert cache.get("a") is None and cache.get("c") == 3
