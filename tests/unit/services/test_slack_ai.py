import asyncio
import json

import pytest

from src.services.slack_ai import (
    JsonCache,
    SlackAI,
    clean_title,
    needs_translation,
    parse_items,
    text_key,
    translate_prompt,
)


class FakeLLM:
    def __init__(self):
        self.prompts = []

    async def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        payload = json.loads(prompt[prompt.rindex("\n\n") + 2:]) if "items" in prompt[-200:] or '"items"' in prompt else {}
        if "中文短标题" in prompt and "items" in payload:
            return json.dumps({"items": [{"id": it["id"], "title": f"《标题{it['id']}》。"} for it in payload["items"]]})
        if "items" in payload:
            return json.dumps({"items": [{"id": it["id"], "zh": "中:" + it["text"]} for it in payload["items"]]})
        return json.dumps({"title": "HBM4 良率讨论", "summary": "Dylan 问良率，Ray 说周五给数据。", "todo_for_me": ""})


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


def test_titles_are_cleaned_and_cached(tmp_path):
    ai, llm = make_ai(tmp_path)
    titles = run(ai.titles_for({"1.1": "Huawei 9050 Teardown Post", "2.2": "", "3.3": "amd"}))
    assert titles == {"1.1": "标题0", "3.3": "标题1"}
    assert run(ai.titles_for({"9.9": "amd"})) == {"9.9": "标题1"}
    assert len(llm.prompts) == 1


def test_summary_cached_by_key(tmp_path):
    ai, llm = make_ai(tmp_path)
    first = run(ai.summary("C1:1.1:2.2", "# thread"))
    assert first["summary"].startswith("Dylan") and first["title"] == "HBM4 良率讨论"
    run(ai.summary("C1:1.1:2.2", "# thread"))
    assert len(llm.prompts) == 1
    run(ai.summary("C1:1.1:3.3", "# thread"))  # 有新回复 -> 重算
    assert len(llm.prompts) == 2


def test_summary_without_text_fails(tmp_path):
    async def empty(prompt):
        return json.dumps({"title": "", "summary": ""})

    ai, _ = make_ai(tmp_path, llm=empty)
    with pytest.raises(ValueError):
        run(ai.summary("k", "# t"))


def test_parse_items_and_helpers(tmp_path):
    assert parse_items({"items": [{"id": "1", "zh": " 好 "}, {"id": 9, "zh": "x"}, "bad"]}, "zh", 2) == [None, "好"]
    assert parse_items([], "zh", 1) == [None]
    assert clean_title("《英伟达封装瓶颈》。") == "英伟达封装瓶颈"
    assert text_key("a") != text_key("b")
    assert '"id": 0' in translate_prompt(["hi there"], "")
    cache = JsonCache(tmp_path / "c.json", limit=2)
    cache.put_many({"a": 1, "b": 2})
    cache.put_many({"c": 3})
    assert cache.get("a") is None and cache.get("c") == 3
