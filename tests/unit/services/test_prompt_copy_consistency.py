# -*- coding: utf-8 -*-
"""提示词副本一致性。

章节标题走独立的提示词链路，不带上「白名单铁律」就会出现「吉瓦」「词元」这类
正文里被明令禁止的写法，与正文形成两套术语。为此 batch_translation_service.py
里保留了一份该小节的 Python 副本。

副本与原文的一致性此前只靠一行注释维系——改了 txt 而忘记同步 Python，标题链路
会静默退回旧规则，而且没有任何测试会失败。这里把它钉死。
"""

import re
from pathlib import Path

from src.services.batch_translation_service import SECTION_TITLE_WHITELIST_RULES

PROMPT_PATH = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "prompts"
    / "longform"
    / "translation"
    / "section_batch_translate.txt"
)


def _whitelist_section() -> str:
    text = PROMPT_PATH.read_text(encoding="utf-8")
    match = re.search(r"(## 白名单铁律.*?)(?=\n## )", text, re.S)
    assert match, "section_batch_translate.txt 里找不到「## 白名单铁律」小节"
    return match.group(1).strip()


def test_section_title_whitelist_matches_prompt_file() -> None:
    assert SECTION_TITLE_WHITELIST_RULES.strip() == _whitelist_section(), (
        "batch_translation_service.SECTION_TITLE_WHITELIST_RULES 与 "
        "section_batch_translate.txt 的「白名单铁律」小节已漂移。"
        "改了其中一处就要同步另一处，否则章节标题会退回旧规则。"
    )


def test_whitelist_still_covers_the_two_easiest_to_miss_rules() -> None:
    # 这两条是实测最常被误译的：token 被汉化、kW/W 被译成千瓦/瓦。
    # 它们从铁律里消失过一次就会立刻反映到成品标题上，值得单独兜底。
    rules = SECTION_TITLE_WHITELIST_RULES
    assert "token" in rules
    assert "kW" in rules and "W/cm²" in rules
