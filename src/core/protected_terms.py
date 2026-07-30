"""Hard output guards for terms that must remain untranslated.

本模块是「token 严禁翻译」规则的**唯一定义源**。长文链路
（:mod:`markdown_postprocess`）与 QA 门禁（:mod:`translation_qa`）都从这里
import，避免三处各写一套正则导致「QA 判死、fixer 修不掉」的死循环。
"""

from __future__ import annotations

import re


_SOURCE_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_])tokens?(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

# 被汉化的 token：词元 / 代币 / 令牌。
# 「令牌桶 / 令牌环」是 token bucket / token ring 的既定网络术语译法，按紧邻
# 组合词豁免；孤立「令牌」仍算汉化。
# 「代币」在加密货币语境下是正规译法，因此**所有**改写路径都必须先过
# :func:`source_mentions_token` 源文守卫。
SINICIZED_TOKEN_RE = re.compile(r"词元|代币|令牌(?![桶环])")

# 「词元化」→「token 化」显式给出空格，保证替换自身幂等（与 CJK–ASCII
# 补空格的结果一致）。
TOKEN_CIYUAN_HUA_RE = re.compile(r"词元化")

_TOKEN_WITH_CHINESE_ANNOTATION_RE = re.compile(
    r"(?<![A-Za-z0-9_])tokens?(?![A-Za-z0-9_])\s*[（(]\s*(?:词元|令牌|代币)\s*[)）]",
    re.IGNORECASE,
)
_CHINESE_WITH_TOKEN_ANNOTATION_RE = re.compile(
    r"(?:词元|令牌|代币)\s*[（(]\s*tokens?\s*[)）]",
    re.IGNORECASE,
)
_TOKEN_SLASH_CHINESE_RE = re.compile(
    r"(?<![A-Za-z0-9_])tokens?(?![A-Za-z0-9_])\s*[/／]\s*(?:词元|令牌|代币)",
    re.IGNORECASE,
)
_CHINESE_SLASH_TOKEN_RE = re.compile(
    r"(?:词元|令牌|代币)\s*[/／]\s*tokens?(?![A-Za-z0-9_])",
    re.IGNORECASE,
)


def source_mentions_token(source_text: str) -> bool:
    """源文里是否出现独立的 ``token`` 一词。

    所有 token 去汉化改写与 QA 判定都以此为前提：源文根本没提 token 时，
    译文里的「令牌」（如 OAuth 访问令牌）、「代币」（加密货币）都是正确
    译法，不得改写、也不该报错。
    """
    return bool(_SOURCE_TOKEN_RE.search(source_text or ""))


def desinicize_token(text: str) -> str:
    """把被汉化的 token 改写回英文原形（不含源文守卫，调用方负责）。"""
    if not text:
        return text
    text = TOKEN_CIYUAN_HUA_RE.sub("token 化", text)
    return SINICIZED_TOKEN_RE.sub("token", text)


def preserve_protected_terms(source_text: str, translated_text: str) -> str:
    """Enforce untranslated terms when they occur in the source.

    ``token`` is an intentional English technical term in this product. The
    guard is source-aware so unrelated Chinese text containing "词元" is not
    rewritten when the source never mentioned the protected term.
    """

    if not translated_text or not source_mentions_token(source_text):
        return translated_text

    normalized = _TOKEN_WITH_CHINESE_ANNOTATION_RE.sub("token", translated_text)
    normalized = _CHINESE_WITH_TOKEN_ANNOTATION_RE.sub("token", normalized)
    normalized = _TOKEN_SLASH_CHINESE_RE.sub("token", normalized)
    normalized = _CHINESE_SLASH_TOKEN_RE.sub("token", normalized)
    normalized = desinicize_token(normalized)

    if normalized == translated_text:
        # 什么都没改写，就不要顺手动人家的排版。
        return translated_text

    # 帖子链路不跑 markdown 后处理，替换出的 token 需要就地补 CJK–ASCII 空格，
    # 否则会得到「token数量」这种没有空格的混排。
    # 但话题标签行必须整行跳过：`#AI芯片` 被插入空格会断成 `#AI` + 裸文字
    # 「芯片」，标签行失效，下游还会因此判定"没有标签"而再追加一行。
    from .markdown_postprocess import normalize_cjk_ascii_spacing
    from .post_hashtags import is_hashtag_only_line

    return "\n".join(
        line if is_hashtag_only_line(line) else normalize_cjk_ascii_spacing(line)
        for line in normalized.split("\n")
    )
