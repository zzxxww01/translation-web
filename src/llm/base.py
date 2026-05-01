"""
Translation Agent - LLM Provider Base

Abstract base class for LLM providers.
"""

from abc import ABC, abstractmethod
import json
import logging
from typing import Optional, List, Dict, Any

from src.settings import settings
from src.core.longform_context import (
    build_article_challenge_payload,
    build_section_guideline_lines,
    limit_format_tokens,
)
from ..core.limits import TranslationLimits


logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """LLM Provider 基类"""

    def __init__(self):
        """初始化Prompt管理器"""
        from ..prompts import get_prompt_manager

        self.prompt_manager = get_prompt_manager()

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
        context_data = dict(context or {})
        prompt = self._build_translation_prompt(text, context_data)
        return self.generate(prompt, temperature=0.5, timeout=timeout)

    def analyze(self, text: str) -> Dict[str, Any]:
        """
        分析文本，提取术语和风格

        Args:
            text: 要分析的文本

        Returns:
            Dict: 分析结果，包括检测到的术语、风格建议等
        """
        prompt = self._build_analysis_prompt(text)

        try:
            response = self.generate(prompt, response_format="json")
            return self._parse_json_response(response)
        except json.JSONDecodeError:
            return {
                "terms": [],
                "style": {"tone": "professional", "formality": "formal", "notes": []},
            }
        except Exception as exc:
            raise RuntimeError(f"Analysis failed: {exc}") from exc

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
        high_freq_terms_list = "\n".join(
            [
                f"{i+1}. **{term['term']}** (出现 {term['frequency']} 次)"
                for i, term in enumerate(high_freq_candidates)
            ]
        )

        prompt = self.prompt_manager.get(
            "longform/analysis/deep_analyze_with_terms",
            outline=outline,
            sampled_text=sampled_text,
            high_freq_terms_list=high_freq_terms_list,
        )
        response = self.generate(
            prompt,
            response_format="json",
            temperature=0.3,
            timeout=timeout,
        )
        return self._parse_json_response(response)

    def deep_analyze_document(
        self,
        outline: str,
        sampled_text: str,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        深度分析文档（不包含术语验证）

        Args:
            outline: 章节大纲
            sampled_text: 采样文本
            timeout: 超时时间（秒）

        Returns:
            Dict: 分析结果，包含theme, key_arguments, structure_summary, style, challenges, guidelines
        """
        prompt = self.prompt_manager.get(
            "longform/analysis/deep_analyze",
            outline=outline,
            sampled_text=sampled_text,
        )
        response = self.generate(
            prompt,
            response_format="json",
            temperature=0.3,
            timeout=timeout,
        )
        return self._parse_json_response(response)

    def verify_high_frequency_terms(
        self,
        sampled_text: str,
        high_freq_candidates: List[Dict[str, Any]],
        timeout: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        验证高频术语候选

        Args:
            sampled_text: 采样文本（用于理解上下文）
            high_freq_candidates: 高频术语候选列表 [{"term": ..., "frequency": ...}, ...]
            timeout: 超时时间（秒）

        Returns:
            List[Dict]: 验证通过的术语列表
        """
        high_freq_terms_list = "\n".join(
            [
                f"{i+1}. **{term['term']}** (出现 {term['frequency']} 次)"
                for i, term in enumerate(high_freq_candidates)
            ]
        )

        prompt = self.prompt_manager.get(
            "longform/analysis/verify_terms",
            sampled_text=sampled_text,
            high_freq_terms_list=high_freq_terms_list,
        )
        response = self.generate(
            prompt,
            response_format="json",
            temperature=0.3,
            timeout=timeout,
        )
        result = self._parse_json_response(response)
        return result.get("verified_terms", [])

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
        prompt = self._build_consistency_prompt(paragraphs, glossary)

        try:
            response = self.generate(prompt, response_format="json")
            result = self._parse_json_response(response)
            return result if isinstance(result, list) else []
        except Exception:
            return []

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
        context_data = dict(context or {})
        prompt = self._build_retranslation_prompt(
            source_text,
            current_translation,
            context_data,
        )
        return self.generate(prompt, temperature=0.4)

    def repair_format_tokens(
        self,
        source_text: str,
        translated_text: str,
        format_tokens: List[Dict[str, Any]],
        issues: Optional[List[str]] = None,
        model: Optional[str] = None,
    ) -> Optional[str]:
        """Run a lightweight repair pass to restore hidden token wrappers."""
        preview_tokens = limit_format_tokens(format_tokens)
        if not preview_tokens:
            return None

        token_lines: List[str] = []
        for token in preview_tokens:
            if not isinstance(token, dict):
                continue
            token_id = str(token.get("id", "")).strip()
            token_type = str(token.get("type", "")).strip()
            token_text = str(token.get("text", "")).strip()
            if token_id:
                token_lines.append(f"- {token_id} ({token_type}): {token_text}")

        issue_lines = [f"- {item}" for item in (issues or []) if str(item).strip()]
        issue_block = "\n".join(issue_lines) if issue_lines else "- (not provided)"
        token_block = "\n".join(token_lines) if token_lines else "- (empty)"

        prompt = "\n".join(
            [
                "You are a token repair engine for long-form translation.",
                "Task: repair hidden backend tokens only.",
                "",
                "Rules:",
                "1. Keep meaning and wording unchanged as much as possible.",
                "2. Restore missing or malformed `[[[TYPE_N|...]]]` wrappers.",
                "3. Keep token ids exactly from the token list.",
                "4. Do not add extra commentary.",
                "5. Output ONLY the repaired translation text.",
                "",
                "Expected tokens:",
                token_block,
                "",
                "Validation issues:",
                issue_block,
                "",
                "Source (tokenized):",
                source_text,
                "",
                "Broken translation:",
                translated_text,
            ]
        )

        repaired = self.generate(prompt, temperature=0.1, model=model).strip()
        if repaired.startswith("```"):
            lines = repaired.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            repaired = "\n".join(lines).strip()
        return repaired or None

    def translate_section(
        self,
        section_text: str,
        section_title: str,
        context: Dict[str, Any],
        paragraph_ids: List[str],
    ) -> List[Dict[str, str]]:
        """Translate one full section with the dedicated section-batch prompt."""
        prompt = self._build_batch_translation_prompt(
            section_text, section_title, context, paragraph_ids
        )

        response = self.generate(prompt, response_format="json", temperature=0.3)
        result = self._parse_json_response(response)

        if isinstance(result, dict) and "translations" in result:
            return result["translations"]
        if isinstance(result, list):
            return result

        raise ValueError(
            "Batch translation response does not satisfy the JSON contract."
        )

    def translate_source_metadata_batch(
        self,
        entries: List[Dict[str, str]],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, str]]:
        """Translate source/citation metadata entries in one batch."""
        prompt = self._build_source_metadata_batch_prompt(entries, context or {})
        response = self.generate(prompt, response_format="json", temperature=0.2)
        result = self._parse_json_response(response)

        if isinstance(result, dict) and "translations" in result:
            return result["translations"]
        if isinstance(result, list):
            return result

        raise ValueError(
            "Source metadata translation response does not satisfy the JSON contract."
        )

    def translate_title(
        self,
        title: str,
        context: Optional[Dict[str, Any]] = None,
        subtitle: Optional[str] = None,
    ) -> Dict[str, str]:
        """Translate article title and optional subtitle in one call."""
        context_lines: List[str] = []
        if context:
            if context.get("article_theme"):
                context_lines.append(f"- Article theme: {context['article_theme']}")
            if context.get("structure_summary"):
                context_lines.append(
                    f"- Structure summary: {context['structure_summary']}"
                )
            if context.get("target_audience"):
                context_lines.append(f"- Target audience: {context['target_audience']}")

        prompt = self.prompt_manager.get(
            "longform/auxiliary/title_translate",
            context_block="\n".join(context_lines) if context_lines else "- None",
            glossary_block=(context or {}).get("glossary_block", "(无命中术语)"),
            preservation_block=(
                (context or {}).get("preservation_block", "- 无额外保留项")
            ),
            title=title,
            subtitle=subtitle or "(无)",
        )
        raw = self.generate(prompt, temperature=0.3)

        result: Dict[str, str] = {}
        for line in raw.strip().splitlines():
            line = line.strip()
            if line.startswith("标题:") or line.startswith("标题："):
                result["title"] = line.split(":", 1)[-1].split("：", 1)[-1].strip()
            elif line.startswith("副标题:") or line.startswith("副标题："):
                val = line.split(":", 1)[-1].split("：", 1)[-1].strip()
                if val:
                    result["subtitle"] = val

        if not result.get("title"):
            result["title"] = raw.strip().splitlines()[0].strip()

        return result

    def translate_section_title(
        self,
        title: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Translate a section title."""
        context_lines: List[str] = []
        if context:
            if context.get("article_theme"):
                context_lines.append(f"- Article theme: {context['article_theme']}")
            if context.get("context"):
                context_lines.append(f"- Context: {context['context']}")
            if context.get("previous_section_title"):
                context_lines.append(
                    f"- Previous section: {context['previous_section_title']}"
                )
            if context.get("next_section_title"):
                context_lines.append(f"- Next section: {context['next_section_title']}")

        prompt = self.prompt_manager.get(
            "longform/auxiliary/section_title_translate",
            context_block="\n".join(context_lines) if context_lines else "- None",
            title=title,
        )
        return self.generate(prompt, temperature=0.3)

    def translate_all_section_titles(
        self,
        sections: List[Dict[str, Any]],
        article_theme: str = "",
    ) -> Dict[str, str]:
        """Translate all section titles in a single API call.

        Args:
            sections: list of dicts with keys:
                - id (str): section identifier
                - title (str): original English title
                - prev (str): previous section title (may be empty)
                - next (str): next section title (may be empty)
            article_theme: article theme from deep analysis

        Returns:
            Dict mapping section_id -> translated Chinese title.
            If a section_id is missing from the result, callers should fall
            back to the per-title ``translate_section_title`` method.
        """
        if not sections:
            return {}

        chapter_lines: List[str] = []
        for i, sec in enumerate(sections, 1):
            sec_id = sec.get("id", f"s{i:02d}")
            title = sec.get("title", "")
            prev_t = sec.get("prev", "")
            next_t = sec.get("next", "")
            parts = [f'{i}. id={sec_id}, title="{title}"']
            if prev_t:
                parts.append(f'prev="{prev_t}"')
            if next_t:
                parts.append(f'next="{next_t}"')
            chapter_lines.append(", ".join(parts))

        theme_line = f"文章主题：{article_theme}" if article_theme else ""
        prompt = "\n".join(
            filter(
                None,
                [
                    "你是一位资深中英双语编辑，尤其擅长硬核科技长文领域。"
                    "请将下面所有章节标题翻译为简洁、自然、契合文章上下文的中文。",
                    "",
                    theme_line,
                    "",
                    "## 章节列表（id, 原标题, 前后章节供参考）",
                    "\n".join(chapter_lines),
                    "",
                    "## 输出规则",
                    '以 JSON 返回，格式：{"translations": {"<id>": "<中文标题>", ...}}',
                    "只输出 JSON，不要解释，不要额外文字。",
                ],
            )
        )

        try:
            raw = self.generate(prompt, response_format="json", temperature=0.3)
            result = self._parse_json_response(raw)
            translations = result.get("translations", {})
            if isinstance(translations, dict):
                logger.info(
                    "[LLMProvider] Batch section title translation: %d/%d titles returned",
                    len(translations),
                    len(sections),
                )
                return {str(k): str(v) for k, v in translations.items()}
        except Exception as exc:
            logger.warning(
                "[LLMProvider] Batch section title translation failed, will use per-title fallback: %s",
                exc,
            )

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
            }
            try:
                results[sec_id] = self.translate_section_title(title, context=context)
            except Exception:
                results[sec_id] = title
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

    def refine_translation(
        self,
        source: str,
        current_translation: str,
        issue_type: str,
        description: str,
        suggestion: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        润色翻译（四步法 Step 4）

        Args:
            source: 原文
            current_translation: 当前译文
            issue_type: 问题类型
            description: 问题描述
            suggestion: 修改建议

        Returns:
            str: 润色后的译文
        """
        prompt = self._build_refine_prompt(
            source,
            current_translation,
            issue_type,
            description,
            suggestion,
            context=context,
        )
        return self.generate(prompt, temperature=0.3)

    def style_polish(
        self,
        source: str,
        current_translation: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        风格润色（四步法 Step 5 - 可选）

        针对简洁性、四字格、隐喻一致性、语气力度做最终打磨。

        Args:
            source: 原文
            current_translation: 当前译文

        Returns:
            str: 润色后的译文
        """
        prompt = self.prompt_manager.get(
            "longform/review/style_polish",
            source=source,
            current_translation=current_translation,
        )
        return self.generate(prompt, temperature=0.3)

    def style_polish_batch(
        self,
        pairs: List[tuple[str, str]],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """
        批量风格润色（优化版 Step 5）

        一次 API 调用润色多个段落，降低成本。

        Args:
            pairs: [(source, current_translation), ...] 原文和译文对
            context: 可选上下文

        Returns:
            List[str]: 润色后的译文列表
        """
        # 构建批量输入
        pairs_text = ""
        for i, (source, translation) in enumerate(pairs):
            pairs_text += f"### 段落 {i}\n\n"
            pairs_text += f"**原文：**\n{source}\n\n"
            pairs_text += f"**当前译文：**\n{translation}\n\n"

        prompt = self.prompt_manager.get(
            "longform/review/style_polish_batch",
            pairs_text=pairs_text,
        )

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

            # 验证数量一致
            if len(polished) != len(pairs):
                logger.warning(
                    f"Batch polish returned {len(polished)} translations, expected {len(pairs)}. "
                    f"Falling back to original translations."
                )
                return [translation for _, translation in pairs]

            return polished

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse batch polish response: {e}")
            logger.debug(f"Response was: {response}")
            # 降级：返回原译文
            return [translation for _, translation in pairs]

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

            # 验证数量一致
            if len(polished) != len(pairs):
                logger.warning(
                    f"Batch refine_and_polish returned {len(polished)} translations, expected {len(pairs)}. "
                    f"Falling back to original translations."
                )
                return [pair["translation"] for pair in pairs]

            return polished

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse batch refine_and_polish response: {e}")
            logger.debug(f"Response was: {response}")
            # 降级：返回原译文
            return [pair["translation"] for pair in pairs]

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

    def _build_translation_prompt(self, text: str, context: Dict[str, Any]) -> str:
        """Build the paragraph translation prompt via the shared prompt builder."""
        from ..prompts.prompt_builder import get_prompt_builder

        builder = get_prompt_builder(style=self._resolve_translation_prompt_style())
        return builder.build_prompt(
            source_text=text,
            glossary=context.get("glossary", []),
            previous_paragraphs=context.get("previous_paragraphs", []),
            next_preview=context.get("next_preview", []),
            article_title=context.get("article_title"),
            article_theme=context.get("article_theme"),
            article_structure=context.get("article_structure"),
            current_section_title=context.get("current_section_title"),
            heading_chain=context.get("heading_chain"),
            target_audience=context.get("target_audience"),
            translation_voice=context.get("translation_voice"),
            article_challenges=context.get("article_challenges"),
            style_guide=context.get("style_guide"),
            section_context=context.get("section_context"),
            learned_rules=context.get("learned_rules"),
            instruction=context.get("instruction"),
            previous_translation=context.get("previous_translation"),
            format_tokens=context.get("format_tokens", []),
            term_usage=context.get("term_usage"),
        )

    def _build_retranslation_prompt(
        self,
        source_text: str,
        current_translation: str,
        context: Dict[str, Any],
    ) -> str:
        """Build the paragraph retranslation prompt via the shared prompt builder."""
        from ..prompts.prompt_builder import get_prompt_builder

        builder = get_prompt_builder(style=self._resolve_translation_prompt_style())
        return builder.build_retranslation_prompt(
            source_text=source_text,
            current_translation=current_translation,
            glossary=context.get("glossary", []),
            previous_paragraphs=context.get("previous_paragraphs", []),
            next_preview=context.get("next_preview", []),
            article_title=context.get("article_title"),
            article_theme=context.get("article_theme"),
            article_structure=context.get("article_structure"),
            current_section_title=context.get("current_section_title"),
            heading_chain=context.get("heading_chain"),
            target_audience=context.get("target_audience"),
            translation_voice=context.get("translation_voice"),
            article_challenges=context.get("article_challenges"),
            style_guide=context.get("style_guide"),
            section_context=context.get("section_context"),
            learned_rules=context.get("learned_rules"),
            instruction=context.get("instruction"),
            format_tokens=context.get("format_tokens", []),
            term_usage=context.get("term_usage"),
        )

    def _resolve_translation_prompt_style(self) -> str:
        style = settings.translation_prompt_style.strip().lower()
        if style not in {"original", "simplified"}:
            return "original"
        return style

    def _build_analysis_prompt(self, text: str) -> str:
        """Build the analysis prompt."""
        return self.prompt_manager.get("analysis", text=text[:8000])

    def _build_consistency_prompt(
        self, paragraphs: List[Dict[str, str]], glossary: Dict[str, str]
    ) -> str:
        """Build the consistency review prompt."""
        para_text = "\n\n".join(
            [
                f"[段落 {i+1}]\n原文：{p['source']}\n译文：{p['translation']}"
                for i, p in enumerate(paragraphs[:20])
            ]
        )

        if isinstance(glossary, list):
            glossary_text = "\n".join(
                [
                    f"- {term.get('original', '')} -> {term.get('translation', '')}"
                    for term in glossary
                    if isinstance(term, dict)
                ]
            )
        elif isinstance(glossary, dict):
            glossary_text = "\n".join(
                [f"- {term} -> {trans}" for term, trans in glossary.items()]
            )
        else:
            glossary_text = "无"

        return self.prompt_manager.get(
            "consistency", para_text=para_text, glossary_text=glossary_text
        )

    def _build_batch_translation_prompt(
        self,
        section_text: str,
        section_title: str,
        context: Dict[str, Any],
        paragraph_ids: List[str],
    ) -> str:
        """Build the section batch translation prompt."""
        format_token_rules = self._format_token_rules_for_prompt(
            context.get("format_tokens", []),
            context.get("format_token_count", 0),
        )
        enhanced_guidelines = build_section_guideline_lines(
            context.get("guidelines", []),
            section_role=context.get("section_role", ""),
            translation_voice=context.get("translation_voice", ""),
            target_audience=context.get("target_audience", ""),
            translation_notes=context.get("translation_notes"),
            format_token_rules=format_token_rules,
        )

        prev_trans = context.get("previous_translations", [])
        if prev_trans:
            prev_lines = []
            for pair in prev_trans[-5:]:
                src_preview = pair.get("source", "")[:80]
                trans_preview = pair.get("translation", "")[:80]
                prev_lines.append(f"- EN: {src_preview}…\n  ZH: {trans_preview}…")
            previous_translations_block = "\n".join(prev_lines)
        else:
            previous_translations_block = "无"

        feedback_block = context.get("feedback_from_previous_sections", "")

        return self.prompt_manager.get(
            "longform/translation/section_batch_translate",
            section_title=section_title,
            section_text=section_text,
            paragraph_ids=json.dumps(paragraph_ids),
            article_theme=context.get("article_theme", ""),
            section_position=context.get("section_position", ""),
            previous_section=context.get("previous_section_title", ""),
            next_section=context.get("next_section_title", ""),
            target_audience=context.get("target_audience", ""),
            translation_voice=context.get("translation_voice", ""),
            article_challenges=self._format_challenges_for_prompt(
                context.get("article_challenges", [])
            ),
            glossary=self._format_glossary_for_prompt(
                context.get("glossary", []),
                term_usage=context.get("term_usage"),
            ),
            guidelines="\n".join(enhanced_guidelines),
            previous_translations=previous_translations_block,
            feedback_from_previous_sections=feedback_block or "无",
        )

    def _build_source_metadata_batch_prompt(
        self,
        entries: List[Dict[str, str]],
        context: Dict[str, Any],
    ) -> str:
        """Build the dedicated batch prompt for source/citation metadata."""
        glossary_block = str(context.get("glossary_block", "")).strip() or "(无命中术语)"
        entries_json = json.dumps(entries, ensure_ascii=False, indent=2)
        return self.prompt_manager.get(
            "longform/metadata/source_batch_translate",
            glossary_block=glossary_block,
            entry_count=len(entries),
            entries_json=entries_json,
        )

    def _format_glossary_for_prompt(
        self,
        glossary: Any,
        term_usage: Optional[Dict[str, List[str]]] = None,
    ) -> str:
        """Render glossary context into prompt-friendly text."""
        from src.core.glossary_prompt import render_glossary_prompt_block

        return render_glossary_prompt_block(
            glossary,
            include_title=False,
            term_usage=term_usage,
            empty_text="无",
        )

    def _format_token_rules_for_prompt(self, tokens: Any, token_count: int = 0) -> str:
        """Render one compact rule block for hidden formatting tokens."""
        preview_tokens = limit_format_tokens(tokens)
        if not preview_tokens and not token_count:
            return ""

        lines = [
            "Hidden token rule: `[[[TYPE_N|...]]]` is a backend control token, not Markdown.",
            "Keep the wrapper, token type, and token id exactly unchanged.",
            "Only translate the text after `|`.",
            "Do not delete, duplicate, renumber, or move tokens to another paragraph.",
        ]
        preview_items = []
        for item in preview_tokens:
            if not isinstance(item, dict):
                continue
            token_id = item.get("id", "")
            token_text = item.get("text", "")
            token_type = item.get("type", "")
            if token_id and token_text:
                preview_items.append(f"{token_id}({token_type}): {token_text}")
        if preview_items:
            lines.append("Tokens in this request: " + "; ".join(preview_items))
        elif token_count:
            lines.append(f"This request contains {token_count} hidden format tokens.")
        return " ".join(lines)

    def _format_challenges_for_prompt(self, challenges: Any) -> str:
        """Render article translation risks into prompt-friendly text."""
        normalized_challenges = build_article_challenge_payload(challenges)
        if not normalized_challenges:
            return "None"

        lines = []
        for item in normalized_challenges:
            location = item.get("location", "")
            issue = item.get("issue", "")
            suggestion = item.get("suggestion", "")
            line = str(issue).strip()
            if location:
                line = f"[{location}] {line}"
            if suggestion:
                line = f"{line}; suggestion: {suggestion}"
            if line:
                lines.append(f"- {line}")

        return "\n".join(lines) if lines else "None"

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

    def _build_refine_prompt(
        self,
        source: str,
        current_translation: str,
        issue_type: str,
        description: str,
        suggestion: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """构建润色 Prompt"""
        base_prompt = self.prompt_manager.get(
            "longform/review/paragraph_revision",
            source=source,
            current_translation=current_translation,
            issue_type=issue_type,
            description=description,
            suggestion=suggestion,
        )
        context_blocks = self._build_refine_context_blocks(context or {})
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

    def _parse_json_response(self, response: str) -> Any:
        """Parse a JSON LLM response with shared cleanup and light repair."""
        text = response.strip()

        if text.startswith("```"):
            lines = text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)

        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            logger.warning(
                "[LLMProvider] Initial JSON parse failed: %s; attempting shared repair",
                exc,
            )

        last_brace = max(text.rfind("}"), text.rfind("]"))
        if last_brace > 0:
            try:
                return json.loads(text[: last_brace + 1])
            except json.JSONDecodeError:
                pass

        fixed = text
        try:
            if fixed.count('"') % 2 != 0:
                last_quote = fixed.rfind('"')
                prev_comma = fixed.rfind(",", 0, last_quote)
                prev_newline = fixed.rfind("\n", 0, last_quote)
                cutoff = max(prev_comma, prev_newline)
                if cutoff > 0:
                    fixed = fixed[:cutoff]

            if fixed.count("{") > fixed.count("}"):
                fixed += "\n}" * (fixed.count("{") - fixed.count("}"))
            if fixed.count("[") > fixed.count("]"):
                fixed += "]" * (fixed.count("[") - fixed.count("]"))

            return json.loads(fixed)
        except json.JSONDecodeError:
            pass

        logger.error("[LLMProvider] Failed to parse JSON response. Preview: %s", text[:500])
        return {}
