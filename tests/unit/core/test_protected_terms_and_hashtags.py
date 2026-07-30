from src.core.format_tokens import build_translation_payload
from src.core.glossary import normalize_glossary_term
from src.core.models import GlossaryTerm, Paragraph, TranslationStrategy
from src.core.post_hashtags import (
    append_xiaohongshu_hashtags,
    select_xiaohongshu_hashtags,
)
from src.core.protected_terms import preserve_protected_terms


def test_token_glossary_entry_is_forced_to_preserve():
    normalized = normalize_glossary_term(
        GlossaryTerm(
            original=" token ",
            translation="词元",
            strategy=TranslationStrategy.PRESERVE_ANNOTATE,
        )
    )

    assert normalized.original == "token"
    assert normalized.translation == "token"
    assert normalized.strategy == TranslationStrategy.PRESERVE
    assert "词元" in normalized.note


def test_protected_token_rewrites_model_translation_and_annotation():
    source = "Each token is processed independently."

    # 替换出的 token 就地补 CJK–ASCII 空格（帖子链路不跑 markdown 后处理，
    # 不补就会得到「每个token」这种没有空格的混排）。
    assert preserve_protected_terms(source, "每个词元都会独立处理。") == "每个 token 都会独立处理。"
    assert preserve_protected_terms(source, "每个token（词元）都会处理。") == "每个 token 都会处理。"
    assert preserve_protected_terms(source, "每个词元（Token）都会处理。") == "每个 token 都会处理。"


def test_protected_token_covers_all_sinicized_forms():
    # 三处规则统一到 protected_terms 之后，帖子链路也认「令牌」「代币」。
    assert (
        preserve_protected_terms("Access token expires.", "访问令牌会过期。")
        == "访问 token 会过期。"
    )
    assert (
        preserve_protected_terms("The token price rose.", "该代币价格上涨。")
        == "该 token 价格上涨。"
    )
    # 「令牌桶」是 token bucket 的既定网络术语译法，豁免。
    assert (
        preserve_protected_terms("A token bucket limiter.", "使用令牌桶限流。")
        == "使用令牌桶限流。"
    )


def test_protected_token_source_guard_covers_crypto_sense():
    # 原文没提 token 时，「代币」（加密货币）是正确译法，不得改写。
    translated = "该代币价格上涨。"
    assert preserve_protected_terms("The coin price rose.", translated) == translated


def test_protected_token_is_source_aware():
    translated = "语言学里也使用词元这个概念。"
    assert preserve_protected_terms("A linguistic concept.", translated) == translated


def test_translation_payload_enforces_token_guard():
    paragraph = Paragraph(
        id="p1",
        index=0,
        source="The model emits one token.",
    )

    payload = build_translation_payload(paragraph, "模型会输出一个词元。")

    assert payload.text == "模型会输出一个 token。"


def test_xiaohongshu_tags_prioritize_specific_topics():
    tags = select_xiaohongshu_hashtags(
        "NVIDIA is building AI chips for a new LLM token workload in semiconductors."
    )

    assert tags == ["#英伟达", "#AI芯片", "#大模型推理"]


def test_xiaohongshu_tags_do_not_use_generic_fallback_for_unclassified_post():
    assert select_xiaohongshu_hashtags("A short general update.") == []


def test_append_xiaohongshu_tags_merges_trailing_tags_without_duplicates():
    result = append_xiaohongshu_hashtags(
        "英伟达发布新一代AI芯片。\n\n#ai #芯片",
        "NVIDIA launches a new AI chip.",
    )

    assert result.endswith("#ai #芯片")
    assert result.count("#ai") == 1
    assert result.count("#芯片") == 1


def test_append_xiaohongshu_tags_caps_existing_and_recommended_tags():
    result = append_xiaohongshu_hashtags(
        "正文\n\n#已有一 #已有二 #已有三 #已有四 #已有五",
        "NVIDIA AI LLM token semiconductor chips",
    )

    assert result.splitlines()[-1].split() == [
        "#已有一",
        "#已有二",
        "#已有三",
        "#已有四",
        "#已有五",
    ]


def test_append_xiaohongshu_tags_does_not_duplicate_inline_tag():
    result = append_xiaohongshu_hashtags(
        "今天聊 #AI 的发展。",
        "AI news",
    )

    assert result.casefold().count("#ai") == 1
    assert result == "今天聊 #AI 的发展。"


def test_append_xiaohongshu_tags_does_not_add_broad_fallback_tags():
    result = append_xiaohongshu_hashtags(
        "正文已有 #科技 #科技资讯 #行业观察。",
        "A general update.",
    )

    assert result == "正文已有 #科技 #科技资讯 #行业观察。"


def test_append_xiaohongshu_tags_filters_generated_generic_tag_line():
    result = append_xiaohongshu_hashtags(
        "英伟达发布新AI芯片。\n\n#科技 #行业观察",
        "NVIDIA launched a new AI chip.",
    )

    assert result.endswith("#英伟达 #AI芯片")
    assert "#科技" not in result
    assert "#行业观察" not in result


def test_append_xiaohongshu_tags_keeps_model_specific_tags_without_padding():
    result = append_xiaohongshu_hashtags(
        "正文\n\n#Blackwell #AI推理",
        "NVIDIA GPU inference update.",
    )

    assert result.endswith("#Blackwell #AI推理")
    assert "#英伟达" not in result


def test_append_xiaohongshu_tags_normalizes_multiline_and_chinese_separators():
    result = append_xiaohongshu_hashtags(
        "正文\n\n#Blackwell、#AI推理\n#GPU，#Blackwell",
        "NVIDIA GPU inference update.",
    )

    assert result == "正文\n\n#Blackwell #AI推理 #GPU"


def test_append_xiaohongshu_tags_filters_generic_multiline_tail():
    result = append_xiaohongshu_hashtags(
        "英伟达推出新AI芯片。\n#科技资讯\n#行业观察、#科技",
        "NVIDIA launched a new AI chip.",
    )

    assert result.endswith("#英伟达 #AI芯片")
    assert "#科技" not in result
    assert "#行业观察" not in result
