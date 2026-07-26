# -*- coding: utf-8 -*-
"""A-2 `](LINK_1)` 畸形占位符残留回归测试（漏检 + 漏还原）。"""

from src.core.format_tokens import (
    build_translation_payload,
    canonicalize_tokenized_markup,
    restore_markdown_from_tokenized,
)
from src.core.models import InlineElement, Paragraph
from src.core.translation_qa import has_critical, run_deterministic_qa


def _link_paragraph() -> Paragraph:
    return Paragraph(
        id="p1",
        index=0,
        source="Read the SemiAnalysis report today.",
        inline_elements=[
            InlineElement(
                type="link",
                text="SemiAnalysis report",
                start=9,
                end=28,
                href="https://semianalysis.com/report",
            )
        ],
    )


def test_canonicalize_recovers_token_id_written_as_url():
    assert (
        canonicalize_tokenized_markup("请阅读[深度报告](LINK_1)。")
        == "请阅读[[[LINK_1|深度报告]]]。"
    )


def test_build_payload_survives_malformed_link_token():
    # 模型把 token id 当 URL 写进 `](LINK_1)`（Nvidia 稿实测）：
    # 规范化后应通过校验，还原时拿回真实 href，不残留 LINK_1。
    paragraph = _link_paragraph()
    payload = build_translation_payload(paragraph, "请阅读[深度报告](LINK_1)。")

    assert payload.format_issues == []
    assert payload.tokenized_text == "请阅读[[[LINK_1|深度报告]]]。"

    restored = restore_markdown_from_tokenized(
        payload.tokenized_text, paragraph.inline_elements
    )
    assert restored == "请阅读[深度报告](https://semianalysis.com/report)。"
    assert "LINK_1" not in restored


def test_restore_handles_residual_malformed_token_directly():
    paragraph = _link_paragraph()
    restored = restore_markdown_from_tokenized(
        "请阅读[深度报告](LINK_1)。", paragraph.inline_elements
    )
    assert restored == "请阅读[深度报告](https://semianalysis.com/report)。"


def test_qa_flags_malformed_token_residue_as_critical():
    issues = run_deterministic_qa("残留 [**深度报告**](LINK_1)外](https://x.com) 未还原")
    codes = {issue.code for issue in issues}
    assert "format_token_residue" in codes
    assert has_critical(issues)
