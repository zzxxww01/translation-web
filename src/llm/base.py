"""
Translation Agent - LLM Provider Base

Abstract base class for LLM providers.
"""

import logging
from abc import ABC, abstractmethod
import logging
from typing import Optional, List, Dict, Any

from ..core.limits import TranslationLimits

logger = logging.getLogger(__name__)


logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """LLM Provider 基类"""

    def __init__(self):
        """初始化Prompt管理器"""
        from ..prompts import get_prompt_manager

        self.prompt_manager = get_prompt_manager()

    @abstractmethod
    def translate(self, text: str, context: Optional[Dict[str, Any]] = None, timeout: Optional[float] = None) -> str:
        """
        翻译文本

        Args:
            text: 要翻译的原文
            context: 上下文信息，包括：
                - glossary: 术语表
                - style_guide: 风格指南
                - previous_paragraphs: 前文已确认译文
                - next_preview: 后文预览
            timeout: 超时时间（秒）

        Returns:
            str: 翻译结果
        """
        pass

    @abstractmethod
    def analyze(self, text: str) -> Dict[str, Any]:
        """
        分析文本，提取术语和风格

        Args:
            text: 要分析的文本

        Returns:
            Dict: 分析结果，包括检测到的术语、风格建议等
        """
        pass

    def deep_analyze_with_term_verification(
        self,
        outline: str,
        sampled_text: str,
        high_freq_candidates: List[Dict[str, Any]],
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        合并深度分析和术语验证（方案6）

        Args:
            outline: 文档大纲
            sampled_text: 采样文本
            high_freq_candidates: 高频术语候选列表
            timeout: 超时时间（秒）

        Returns:
            Dict: 合并分析结果，包括：
                - theme: 主题
                - key_arguments: 关键论点
                - structure_summary: 结构总结
                - sampled_terms: 从采样文本提取的术语
                - verified_high_freq_terms: 验证后的高频术语
                - style: 风格
                - challenges: 翻译难点
                - guidelines: 翻译指南
        """
        raise NotImplementedError(
            "This provider does not implement deep_analyze_with_term_verification."
        )

    @abstractmethod
    def deep_analyze_document(
        self,
        outline: str,
        sampled_text: str,
        timeout: Optional[int] = None
    ) -> Dict:
        """
        深度分析文档（不包含术语验证）

        Args:
            outline: 章节大纲
            sampled_text: 采样文本
            timeout: 超时时间（秒）

        Returns:
            Dict: 分析结果，包含theme, key_arguments, structure_summary, style, challenges, guidelines
        """
        raise NotImplementedError(
            "This provider does not implement deep_analyze_document."
        )

    @abstractmethod
    def verify_high_frequency_terms(
        self,
        sampled_text: str,
        high_freq_candidates: List[Dict],
        timeout: Optional[int] = None
    ) -> List[Dict]:
        """
        验证高频术语候选

        Args:
            sampled_text: 采样文本（用于理解上下文）
            high_freq_candidates: 高频术语候选列表 [{"term": ..., "frequency": ...}, ...]
            timeout: 超时时间（秒）

        Returns:
            List[Dict]: 验证通过的术语列表
        """
        raise NotImplementedError(
            "This provider does not implement verify_high_frequency_terms."
        )

    @abstractmethod
    def check_consistency(
        self, paragraphs: List[Dict[str, str]], glossary: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        检查译文一致性

        Args:
            paragraphs: 段落列表 [{"source": ..., "translation": ...}, ...]
            glossary: 术语表 {term: translation, ...}

        Returns:
            List[Dict]: 问题列表
        """
        pass

    @abstractmethod
    def generate(
        self,
        prompt: str,
        response_format: Optional[str] = None,
        temperature: float = 0.7,
        model: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        通用文本生成（用于四步法的各个步骤）

        Args:
            prompt: 提示词
            response_format: 响应格式，"json" 表示期望 JSON 输出
            temperature: 温度参数
            model: 可选模型选择器（仅供内部方法覆盖默认模型，如 prescan 使用 flash）

        Returns:
            str: 生成的文本
        """
        pass

    def retranslate(
        self,
        source_text: str,
        current_translation: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Retranslate one paragraph with the dedicated longform retranslation prompt."""
        raise NotImplementedError(
            "This provider does not implement paragraph retranslation."
        )

    def repair_format_tokens(
        self,
        source_text: str,
        translated_text: str,
        format_tokens: List[Dict[str, Any]],
        issues: Optional[List[str]] = None,
        model: Optional[str] = None,
    ) -> Optional[str]:
        """Try to repair broken hidden format tokens after validation fails."""
        return None

    def translate_section(
        self,
        section_text: str,
        section_title: str,
        context: Dict[str, Any],
        paragraph_ids: List[str],
    ) -> List[Dict[str, str]]:
        """Translate one full section with the dedicated section-batch prompt."""
        raise NotImplementedError(
            "This provider does not implement section batch translation."
        )

    def translate_source_metadata_batch(
        self,
        entries: List[Dict[str, str]],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, str]]:
        """Translate source/citation metadata entries in one batch."""
        raise NotImplementedError(
            "This provider does not implement source metadata batch translation."
        )

    def translate_title(
        self,
        title: str,
        context: Optional[Dict[str, Any]] = None,
        subtitle: Optional[str] = None,
    ) -> Dict[str, str]:
        """Translate article title and optional subtitle in one call."""
        raise NotImplementedError(
            "This provider does not implement article title translation."
        )

    def translate_section_title(
        self,
        title: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Translate a section title."""
        raise NotImplementedError(
            "This provider does not implement section title translation."
        )

    def translate_all_section_titles(
        self,
        sections: List[Dict[str, Any]],
        article_theme: str = "",
        *,
        glossary_block: str = "",
        whitelist_rules: str = "",
    ) -> Dict[str, str]:
        """Translate all section titles in a single API call.

        Args:
            sections: list of dicts with keys:
                - id (str): section identifier
                - title (str): original English title
                - prev (str): previous section title (may be empty)
                - next (str): next section title (may be empty)
            article_theme: article theme from deep analysis
            glossary_block: 命中术语块，保证标题与正文用同一套术语
            whitelist_rules: 「永不翻译」白名单铁律（token / GW·MW·kW 等）

        Returns:
            Dict mapping section_id -> translated Chinese title.
            If a section_id is missing from the result, callers should fall
            back to the per-title ``translate_section_title`` method.
        """
        # Default fallback: call translate_section_title one by one.
        results: Dict[str, str] = {}
        for sec in sections:
            sec_id = sec.get("id", "")
            title = sec.get("title", "")
            if not title:
                continue
            context = {
                "article_theme": article_theme,
                "context": "Section heading inside a long-form article",
                "previous_section_title": sec.get("prev", ""),
                "next_section_title": sec.get("next", ""),
                "glossary_block": glossary_block,
                "whitelist_rules": whitelist_rules,
            }
            try:
                results[sec_id] = self.translate_section_title(title, context=context)
            except Exception:
                results[sec_id] = title  # keep original on failure
        return results

    def deep_analyze(
        self,
        text: str,
        sections_outline: str,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        深度分析文本（Phase 0）

        Args:
            text: 全文内容
            sections_outline: 章节大纲
            timeout: 可选的单次调用超时时间（秒）

        Returns:
            Dict: 深度分析结果
        """
        # 默认实现调用 generate，子类可以覆盖
        prompt = self._build_deep_analysis_prompt(text, sections_outline)
        response = self.generate(prompt, response_format="json", timeout=timeout)
        return self._parse_json_response(response)

    def reflect_on_translation(
        self,
        source_paragraphs: List[str],
        translations: List[str],
        guidelines: List[str],
        terminology: List[Dict],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        反思翻译质量（四步法 Step 3）

        Args:
            source_paragraphs: 原文段落列表
            translations: 译文列表
            guidelines: 翻译指南
            terminology: 术语表

                   Dict: 反思结果
        """
        prompt = self._build_reflection_prompt(
            source_paragraphs,
            translations,
            guidelines,
            terminology,
            context=context,
        )
        response = self.generate(prompt, response_format="json")
        return self._parse_json_response(response)

    def refine_and_polish_batch(
        self,
        pairs: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """
        批量润色（合并 Step 4 和 Step 5）

        一次 API 调用同时处理问题修复和风格优化。

        Args:
            pairs: 段落列表，每个包含:
                - source: 原文
                - translation: 当前译文
                - issues: 问题列表 (可选)
            context: 上下文信息（术语表、reflection_scores 等）

        Returns:
            List[str]: 润色后的译文列表
        """
        # 从 context 中提取 reflection_scores
        reflection_scores = context.get("reflection_scores", {}) if context else {}

        prompt = self._build_refine_and_polish_prompt(pairs, reflection_scores, context)
        response = self.generate(prompt, temperature=0.3)

        # 解析 JSON 响应
        import json
        try:
            # 提取 JSON 部分
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            elif "```" in response:
                json_start = response.find("```") + 3
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            else:
                json_str = response.strip()

            result = json.loads(json_str)
            polished = result.get("polished_translations", [])
            return self._align_polished_batch(polished, pairs)

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse batch refine_and_polish response: {e}")
            logger.debug(f"Response was: {response}")
            # 降级：返回原译文
            return [pair["translation"] for pair in pairs]

    def _align_polished_batch(
        self,
        polished: Any,
        pairs: List[Dict[str, Any]],
    ) -> List[str]:
        """把批量润色结果对齐回输入段落顺序。

        新契约返回 `[{"index": 0, "translation": "..."}]`，按 index 归位；
        旧契约返回裸字符串数组，按位置回落（模型不遵守新契约时不至于整批降级）。
        两种格式下缺失、越界或非字符串的条目一律回退该段原译文，避免"数量凑够但
        内容错位"静默通过（审计 TR12）。
        """
        originals = [pair.get("translation", "") for pair in pairs]

        if not isinstance(polished, list) or not polished:
            logger.warning(
                "Batch refine_and_polish returned no usable translations (%s); "
                "falling back to original translations.",
                type(polished).__name__,
            )
            return originals

        has_indexed_items = any(isinstance(item, dict) for item in polished)

        if has_indexed_items:
            by_index: Dict[int, str] = {}
            for position, item in enumerate(polished):
                if not isinstance(item, dict):
                    # 混合数组（部分带 index、部分是裸字符串）：裸字符串按它在
                    # 数组里的位置补位，不然会被静默丢弃、只在 missing 计数里
                    # 露一下头。带 index 的条目优先，后面统一覆盖。
                    if (
                        isinstance(item, str)
                        and item.strip()
                        and 0 <= position < len(originals)
                    ):
                        by_index.setdefault(position, item)
                    continue
                try:
                    index = int(item.get("index"))
                except (TypeError, ValueError):
                    logger.warning(
                        "Batch refine_and_polish item has invalid index: %r", item.get("index")
                    )
                    continue
                text = item.get("translation")
                if not isinstance(text, str) or not text.strip():
                    continue
                if not 0 <= index < len(originals):
                    logger.warning(
                        "Batch refine_and_polish index %s out of range (batch size %s); skipped.",
                        index, len(originals),
                    )
                    continue
                # 显式带 index 的条目优先于按位置补位的裸字符串。
                by_index[index] = text

            missing = [i for i in range(len(originals)) if i not in by_index]
            if missing:
                logger.warning(
                    "Batch refine_and_polish missing %s/%s paragraphs (index %s); "
                    "keeping their original translations.",
                    len(missing), len(originals), missing,
                )
            return [by_index.get(i, originals[i]) for i in range(len(originals))]

        # 旧格式：裸字符串数组，只能按位置对齐，长度不符则整批回退
        if len(polished) != len(pairs):
            logger.warning(
                "Batch refine_and_polish returned %s translations, expected %s. "
                "Falling back to original translations.",
                len(polished), len(pairs),
            )
            return originals

        return [
            item if isinstance(item, str) and item.strip() else originals[i]
            for i, item in enumerate(polished)
        ]

    def prescan_section(
        self,
        section_id: str,
        section_title: str,
        section_content: str,
        existing_terms: Dict[str, str],
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        章节预扫描（方案 C - Phase 1 Step 1）

        使用 Flash 模型快速扫描章节，提取新术语。
        长章节自动分段调用并合并去重。

        Args:
            section_id: 章节 ID
            section_title: 章节标题
            section_content: 章节内容
            existing_terms: 已有术语表 {term: translation}
            model: 可选模型覆盖（如 "flash"）

        Returns:
            Dict: 预扫描结果
            {
                "new_terms": [...],
                "term_usages": {...}
            }
        """
        # 格式化已有术语
        existing_terms_text = (
            "\n".join([f"- {term} → {trans}" for term, trans in existing_terms.items()])
            if existing_terms
            else "无"
        )

        if len(section_content) <= TranslationLimits.PRESCAN_SINGLE_CALL_LIMIT:
            prompt = self._build_prescan_prompt(
                section_id=section_id,
                section_title=section_title,
                section_content=section_content,
                existing_terms=existing_terms_text,
            )
            response = self.generate(
                prompt, response_format="json", temperature=0.3, model=model
            )
            return self._parse_json_response(response)

        # 分段处理
        chunks = self._split_content_for_prescan(section_content, max_chars=TranslationLimits.PRESCAN_CHUNK_SIZE)
        all_new_terms: Dict[str, Dict] = {}
        all_term_usages: Dict[str, str] = {}
        for i, chunk in enumerate(chunks):
            prompt = self._build_prescan_prompt(
                section_id=f"{section_id}_chunk{i}",
                section_title=section_title,
                section_content=chunk,
                existing_terms=existing_terms_text,
            )
            result = self._parse_json_response(
                self.generate(
                    prompt, response_format="json", temperature=0.3, model=model
                )
            )
            for t in result.get("new_terms", []):
                term_key = (t.get("term") or "").lower()
                if term_key and term_key not in all_new_terms:
                    all_new_terms[term_key] = t
            for k, v in result.get("term_usages", {}).items():
                if k not in all_term_usages:
                    all_term_usages[k] = v

        return {
            "new_terms": list(all_new_terms.values()),
            "term_usages": all_term_usages,
        }

    def _split_content_for_prescan(
        self, content: str, max_chars: int = TranslationLimits.PRESCAN_CHUNK_SIZE
    ) -> List[str]:
        """按段落边界分割内容用于 prescan"""
        paragraphs = content.split("\n\n")
        chunks: List[str] = []
        current_chunk: List[str] = []
        current_len = 0

        for para in paragraphs:
            para_len = len(para)
            if current_len + para_len > max_chars and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_len = 0
            current_chunk.append(para)
            current_len += para_len + 2  # +2 for "\n\n"

        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        return chunks if chunks else [content[:max_chars]]

    def prescan_section_with_flash(
        self,
        section_id: str,
        section_title: str,
        section_content: str,
        existing_terms: Dict[str, str],
    ) -> Dict[str, Any]:
        """Prescan one section using the preview model.

        The current Gemini setup rejects `flash` for this environment, while
        `preview` remains available and provides equal-or-better quality.
        """
        return self.prescan_section(
            section_id=section_id,
            section_title=section_title,
            section_content=section_content,
            existing_terms=existing_terms,
        )

    # ============ Prompt Building Methods ============

    def _build_deep_analysis_prompt(self, text: str, sections_outline: str) -> str:
        """构建深度分析 Prompt。"""
        return self.prompt_manager.get(
            "longform/analysis/article_analysis",
            sections_outline=sections_outline,
            text=text[:18000],
        )

    def _build_reflection_prompt(
        self,
        source_paragraphs: List[str],
        translations: List[str],
        guidelines: List[str],
        terminology: List[Dict],
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """构建反思 Prompt"""
        # 构建原文和译文对照
        pairs = []
        for i, (src, trans) in enumerate(zip(source_paragraphs, translations)):
            pairs.append(f"[段落 {i}]\n原文：{src}\n译文：{trans}")
        pairs_text = "\n\n".join(pairs)

        # 构建术语表
        terms_text = "\n".join(
            [
                f"- {t.get('term', t.get('original', ''))} → {t.get('translation', '')}"
                for t in terminology
            ]
        )

        # 构建指南
        guidelines_text = "\n".join([f"- {g}" for g in guidelines])

        base_prompt = self.prompt_manager.get(
            "longform/review/section_critique",
            pairs_text=pairs_text,
            guidelines_text=guidelines_text,
            terms_text=terms_text,
        )

        context_blocks = self._build_reflection_context_blocks(context or {})
        if context_blocks:
            return "\n\n".join(context_blocks + [base_prompt])
        return base_prompt

    def _build_refine_and_polish_prompt(
        self,
        pairs: List[Dict[str, Any]],
        reflection_scores: Dict[str, float],
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """构建批量润色 Prompt（合并问题修复和风格优化）"""
        # 构建段落对照
        pairs_text_list = []
        for i, pair in enumerate(pairs):
            src = pair.get("source", "")
            trans = pair.get("translation", "")
            issues = pair.get("issues", [])

            pair_text = f"[段落 {i}]\n原文：{src}\n当前译文：{trans}"

            if issues:
                issues_text = "\n".join([
                    f"  - [{issue.get('type', 'unknown')}] {issue.get('description', '')}"
                    for issue in issues
                ])
                pair_text += f"\n问题：\n{issues_text}"

            pairs_text_list.append(pair_text)

        pairs_text = "\n\n".join(pairs_text_list)

        # 构建评分信息
        scores_text = ", ".join([
            f"{k}={v:.1f}" for k, v in reflection_scores.items()
        ])
        issues_summary = self._build_refine_issue_summary(pairs)

        base_prompt = self.prompt_manager.get(
            "longform/review/refine_and_polish_batch",
            pairs_text=pairs_text,
            scores_text=scores_text,
            issues_summary=issues_summary,
            terminology_score=float(reflection_scores.get("terminology", 0.0) or 0.0),
            accuracy_score=float(reflection_scores.get("accuracy", 0.0) or 0.0),
            fluency_score=float(reflection_scores.get("fluency", 0.0) or 0.0),
            conciseness_score=float(reflection_scores.get("conciseness", 0.0) or 0.0),
            consistency_score=float(reflection_scores.get("consistency", 0.0) or 0.0),
            logic_score=float(reflection_scores.get("logic", 0.0) or 0.0),
        )

        context_blocks = self._build_refine_context_blocks(context or {})
        if context_blocks:
            return "\n\n".join(context_blocks + [base_prompt])
        return base_prompt

    def _build_refine_issue_summary(self, pairs: List[Dict[str, Any]]) -> str:
        """Summarize batch issues for the refine/polish prompt."""
        lines = []
        for index, pair in enumerate(pairs):
            issues = pair.get("issues", [])
            if not issues:
                continue
            for issue in issues:
                priority = issue.get("priority", "P2")
                issue_type = issue.get("type", "unknown")
                description = issue.get("description", "")
                suggestion = issue.get("suggestion", "")
                line = f"- 段落 {index} [{priority}/{issue_type}]: {description}"
                if suggestion:
                    line += f"；建议：{suggestion}"
                lines.append(line)
        return "\n".join(lines) if lines else "无明确问题；请仅在确有必要时做轻量润色。"

    def _build_reflection_context_blocks(
        self,
        context: Dict[str, Any],
    ) -> List[str]:
        """Attach article and section review context ahead of critique prompts."""
        from src.core.longform_context import (
            build_article_challenge_payload,
            build_review_priorities,
            limit_non_empty_strings,
        )

        if not context:
            return []

        blocks: List[str] = []

        article_lines: List[str] = []
        if context.get("article_theme"):
            article_lines.append(f"文章主题：{context['article_theme']}")
        if context.get("structure_summary"):
            article_lines.append(f"结构摘要：{context['structure_summary']}")
        if context.get("target_audience"):
            article_lines.append(f"目标读者：{context['target_audience']}")
        if context.get("translation_voice"):
            article_lines.append(f"建议中文声线：{context['translation_voice']}")
        if article_lines:
            blocks.append("## 全文背景\n" + "\n".join(article_lines))

        section_lines: List[str] = []
        if context.get("section_title"):
            section_lines.append(f"当前章节：{context['section_title']}")
        if context.get("section_role"):
            section_lines.append(f"章节角色：{context['section_role']}")
        if context.get("relation_to_previous"):
            section_lines.append(f"与前文关系：{context['relation_to_previous']}")
        if context.get("relation_to_next"):
            section_lines.append(f"与后文关系：{context['relation_to_next']}")
        if section_lines:
            blocks.append("## 篇章位置\n" + "\n".join(section_lines))

        notes = limit_non_empty_strings(context.get("translation_notes"), 4)
        if notes:
            blocks.append(
                "## 本章翻译注意点\n" + "\n".join(f"- {note}" for note in notes)
            )

        challenges = build_article_challenge_payload(context.get("article_challenges"))
        if challenges:
            challenge_lines = []
            for challenge in challenges:
                if isinstance(challenge, dict):
                    location = str(challenge.get("location", "")).strip()
                    issue = str(challenge.get("issue", "")).strip()
                    suggestion = str(challenge.get("suggestion", "")).strip()
                    line = issue
                    if location:
                        line = f"[{location}] {line}"
                    if suggestion:
                        line = f"{line}；建议：{suggestion}"
                    if line:
                        challenge_lines.append(f"- {line}")
            if challenge_lines:
                blocks.append("## 全文高风险点\n" + "\n".join(challenge_lines))

        priorities = build_review_priorities(context.get("review_priorities"))
        if priorities:
            blocks.append(
                "## 本轮批评优先级\n" + "\n".join(f"- {item}" for item in priorities)
            )

        return blocks

    def _build_refine_context_blocks(
        self,
        context: Dict[str, Any],
    ) -> List[str]:
        """Attach section-level guardrails to targeted revision prompts."""
        from src.core.longform_context import (
            build_article_challenge_payload,
            build_review_term_entries,
            build_translation_guidelines,
            limit_format_tokens,
        )

        if not context:
            return []

        blocks: List[str] = []
        format_tokens = limit_format_tokens(context.get("format_tokens"))
        if format_tokens:
            token_lines = [
                "## Hidden Format Tokens",
                "- Source and current translation may contain backend tokens like `[[[LINK_1|...]]]`.",
                "- Keep the token wrapper, token id, and token order exactly unchanged.",
                "- Only revise the text after `|`.",
                "- Do not convert these tokens into Markdown syntax.",
            ]
            for token in format_tokens:
                token_id = token.get("id", "")
                token_type = token.get("type", "")
                token_text = token.get("text", "")
                if token_id and token_text:
                    token_lines.append(f"- {token_id} ({token_type}): {token_text}")
            blocks.append("\n".join(token_lines))

        section_lines: List[str] = []
        if context.get("section_title"):
            section_lines.append(f"当前章节：{context['section_title']}")
        if context.get("section_role"):
            section_lines.append(f"章节角色：{context['section_role']}")
        if context.get("target_audience"):
            section_lines.append(f"目标读者：{context['target_audience']}")
        if context.get("translation_voice"):
            section_lines.append(f"目标语气：{context['translation_voice']}")
        if section_lines:
            blocks.append("## 修订上下文\n" + "\n".join(section_lines))

        guidelines = build_translation_guidelines(context.get("guidelines"))
        if guidelines:
            blocks.append(
                "## 修订时仍需遵守\n" + "\n".join(f"- {item}" for item in guidelines)
            )

        terminology = build_review_term_entries(context.get("terminology"))
        if terminology:
            term_lines = []
            for term in terminology:
                original = term.get("term") or term.get("original") or ""
                translation = term.get("translation") or ""
                if original and translation:
                    term_lines.append(f"- {original} -> {translation}")
            if term_lines:
                blocks.append("## 关键术语\n" + "\n".join(term_lines))

        challenges = build_article_challenge_payload(context.get("article_challenges"))
        if challenges:
            challenge_lines = []
            for challenge in challenges:
                if not isinstance(challenge, dict):
                    continue
                location = str(challenge.get("location", "")).strip()
                issue = str(challenge.get("issue", "")).strip()
                suggestion = str(challenge.get("suggestion", "")).strip()
                line = issue
                if location:
                    line = f"[{location}] {line}"
                if suggestion:
                    line = f"{line}；建议：{suggestion}"
                if line:
                    challenge_lines.append(f"- {line}")
            if challenge_lines:
                blocks.append("## 全文高风险点\n" + "\n".join(challenge_lines))

        return blocks

    def _build_prescan_prompt(
        self,
        section_id: str,
        section_title: str,
        section_content: str,
        existing_terms: str,
    ) -> str:
        """构建章节预扫描 Prompt（方案 C 新增）"""
        return self.prompt_manager.get(
            "longform/terminology/section_prescan",
            section_id=section_id,
            section_title=section_title,
            section_content=section_content,
            existing_terms=existing_terms,
        )

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """解析 JSON 响应。

        解析失败时不再静默返回 {}：先尝试从可能含截断/前后赘述的文本中提取
        最大的平衡 {...} / [...] 子串再解析；仍失败才返回 {} 兜底，并记录
        warning（含截断预览），避免分析/术语数据被静默丢弃而无任何信号。
        """
        import json

        text = response.strip()

        # 移除可能的 markdown 代码块标记
        if text.startswith("```"):
            lines = text.split("\n")
            # 移除第一行和最后一行
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 容错恢复：截取首个 { 或 [ 到末个匹配 } 或 ] 的子串再试
        recovered = self._extract_balanced_json(text)
        if recovered is not None:
            try:
                parsed = json.loads(recovered)
                logger.warning(
                    "[LLM] JSON 直接解析失败，已通过平衡括号子串恢复（原长度=%d）。",
                    len(text),
                )
                return parsed
            except json.JSONDecodeError:
                pass

        logger.warning(
            "[LLM] JSON 解析失败，返回空结果。可能是输出被 max_output_tokens 截断或含赘述。预览=%r",
            text[:200],
        )
        return {}

    @staticmethod
    def _extract_balanced_json(text: str) -> Optional[str]:
        """从文本中提取首个完整平衡的 JSON 对象/数组子串（容忍前后赘述）。"""
        start = None
        for i, ch in enumerate(text):
            if ch in "{[":
                start = i
                break
        if start is None:
            return None

        open_ch = text[start]
        close_ch = "}" if open_ch == "{" else "]"
        depth = 0
        in_string = False
        escaped = False
        for i in range(start, len(text)):
            ch = text[i]
            if in_string:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == open_ch:
                depth += 1
            elif ch == close_ch:
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
        return None
