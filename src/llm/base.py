"""
Translation Agent - LLM Provider Base

Abstract base class for LLM providers.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any


class LLMProvider(ABC):
    """LLM Provider 基类"""

    def __init__(self):
        """初始化Prompt管理器"""
        from ..prompts import get_prompt_manager
        self.prompt_manager = get_prompt_manager()

    @abstractmethod
    def translate(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        翻译文本

        Args:
            text: 要翻译的原文
            context: 上下文信息，包括：
                - glossary: 术语表
                - style_guide: 风格指南
                - previous_paragraphs: 前文已确认译文
                - next_preview: 后文预览

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

    @abstractmethod
    def check_consistency(
        self,
        paragraphs: List[Dict[str, str]],
        glossary: Dict[str, str]
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
        raise NotImplementedError("This provider does not implement paragraph retranslation.")

    def translate_section(
        self,
        section_text: str,
        section_title: str,
        context: Dict[str, Any],
        paragraph_ids: List[str],
    ) -> List[Dict[str, str]]:
        """Translate one full section with the dedicated section-batch prompt."""
        raise NotImplementedError("This provider does not implement section batch translation.")

    def translate_title(
        self,
        title: str,
        context: Optional[Dict[str, Any]] = None,
        subtitle: Optional[str] = None,
    ) -> Dict[str, str]:
        """Translate article title and optional subtitle in one call."""
        raise NotImplementedError("This provider does not implement article title translation.")

    def translate_section_title(
        self,
        title: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Translate a section title."""
        raise NotImplementedError("This provider does not implement section title translation.")

    def deep_analyze(self, text: str, sections_outline: str) -> Dict[str, Any]:
        """
        深度分析文本（Phase 0）

        Args:
            text: 全文内容
            sections_outline: 章节大纲

        Returns:
            Dict: 深度分析结果
        """
        # 默认实现调用 generate，子类可以覆盖
        prompt = self._build_deep_analysis_prompt(text, sections_outline)
        response = self.generate(prompt, response_format="json")
        return self._parse_json_response(response)

    def reflect_on_translation(
        self,
        source_paragraphs: List[str],
        translations: List[str],
        guidelines: List[str],
        terminology: List[Dict],
        context: Optional[Dict[str, Any]] = None
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
        context: Optional[Dict[str, Any]] = None
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
        existing_terms_text = "\n".join([
            f"- {term} → {trans}"
            for term, trans in existing_terms.items()
        ]) if existing_terms else "无"

        if len(section_content) <= 7000:
            prompt = self._build_prescan_prompt(
                section_id=section_id,
                section_title=section_title,
                section_content=section_content,
                existing_terms=existing_terms_text
            )
            response = self.generate(prompt, response_format="json", temperature=0.3, model=model)
            return self._parse_json_response(response)

        # 分段处理
        chunks = self._split_content_for_prescan(section_content, max_chars=6000)
        all_new_terms: Dict[str, Dict] = {}
        all_term_usages: Dict[str, list] = {}
        for i, chunk in enumerate(chunks):
            prompt = self._build_prescan_prompt(
                section_id=f"{section_id}_chunk{i}",
                section_title=section_title,
                section_content=chunk,
                existing_terms=existing_terms_text
            )
            result = self._parse_json_response(
                self.generate(prompt, response_format="json", temperature=0.3, model=model)
            )
            for t in result.get("new_terms", []):
                term_key = (t.get("term") or "").lower()
                if term_key and term_key not in all_new_terms:
                    all_new_terms[term_key] = t
            for k, v in result.get("term_usages", {}).items():
                all_term_usages.setdefault(k, []).extend(v if isinstance(v, list) else [v])

        return {"new_terms": list(all_new_terms.values()), "term_usages": all_term_usages}

    def _split_content_for_prescan(self, content: str, max_chars: int = 6000) -> List[str]:
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
        """Prescan one section using the flash model for speed."""
        return self.prescan_section(
            section_id=section_id,
            section_title=section_title,
            section_content=section_content,
            existing_terms=existing_terms,
            model="flash",
        )

    # ============ Prompt Building Methods ============

    def _build_deep_analysis_prompt(self, text: str, sections_outline: str) -> str:
        """构建深度分析 Prompt（方案 C：增加到 30000 字符）"""
        return self.prompt_manager.get(
            "longform/analysis/article_analysis.v2",
            sections_outline=sections_outline,
            text=text[:30000],
        )

    def _build_reflection_prompt(
        self,
        source_paragraphs: List[str],
        translations: List[str],
        guidelines: List[str],
        terminology: List[Dict],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """构建反思 Prompt"""
        # 构建原文和译文对照
        pairs = []
        for i, (src, trans) in enumerate(zip(source_paragraphs, translations)):
            pairs.append(f"[段落 {i}]\n原文：{src}\n译文：{trans}")
        pairs_text = "\n\n".join(pairs)

        # 构建术语表
        terms_text = "\n".join([
            f"- {t.get('term', t.get('original', ''))} → {t.get('translation', '')}"
            for t in terminology
        ])

        # 构建指南
        guidelines_text = "\n".join([f"- {g}" for g in guidelines])

        base_prompt = self.prompt_manager.get(
            "longform/review/section_critique.v2",
            pairs_text=pairs_text,
            guidelines_text=guidelines_text,
            terms_text=terms_text
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
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """构建润色 Prompt"""
        base_prompt = self.prompt_manager.get(
            "longform/review/paragraph_revision.v2",
            source=source,
            current_translation=current_translation,
            issue_type=issue_type,
            description=description,
            suggestion=suggestion
        )
        context_blocks = self._build_refine_context_blocks(context or {})
        if context_blocks:
            return "\n\n".join(context_blocks + [base_prompt])
        return base_prompt

    def _build_reflection_context_blocks(
        self,
        context: Dict[str, Any],
    ) -> List[str]:
        """Attach article and section review context ahead of critique prompts."""
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

        notes = context.get("translation_notes") or []
        if notes:
            blocks.append(
                "## 本章翻译注意点\n" + "\n".join(f"- {note}" for note in notes[:6])
            )

        challenges = context.get("article_challenges") or []
        if challenges:
            challenge_lines = []
            for challenge in challenges[:5]:
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

        priorities = context.get("review_priorities") or []
        if priorities:
            blocks.append(
                "## 本轮批评优先级\n"
                + "\n".join(f"- {item}" for item in priorities[:6])
            )

        return blocks

    def _build_refine_context_blocks(
        self,
        context: Dict[str, Any],
    ) -> List[str]:
        """Attach section-level guardrails to targeted revision prompts."""
        if not context:
            return []

        blocks: List[str] = []
        format_tokens = context.get("format_tokens") or []
        if format_tokens:
            token_lines = [
                "## Hidden Format Tokens",
                "- Source and current translation may contain backend tokens like `[[[LINK_1|...]]]`.",
                "- Keep the token wrapper, token id, and token order exactly unchanged.",
                "- Only revise the text after `|`.",
                "- Do not convert these tokens into Markdown syntax.",
            ]
            for token in format_tokens[:8]:
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

        guidelines = context.get("guidelines") or []
        if guidelines:
            blocks.append(
                "## 修订时仍需遵守\n" + "\n".join(f"- {item}" for item in guidelines[:8])
            )

        terminology = context.get("terminology") or []
        if terminology:
            term_lines = []
            for term in terminology[:12]:
                original = term.get("term") or term.get("original") or ""
                translation = term.get("translation") or ""
                if original and translation:
                    term_lines.append(f"- {original} -> {translation}")
            if term_lines:
                blocks.append("## 关键术语\n" + "\n".join(term_lines))

        challenges = context.get("article_challenges") or []
        if challenges:
            challenge_lines = []
            for challenge in challenges[:4]:
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
        existing_terms: str
    ) -> str:
        """构建章节预扫描 Prompt（方案 C 新增）"""
        return self.prompt_manager.get(
            "longform/terminology/section_prescan.v2",
            section_id=section_id,
            section_title=section_title,
            section_content=section_content,
            existing_terms=existing_terms
        )

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """解析 JSON 响应"""
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
            # 返回空结果
            return {}
