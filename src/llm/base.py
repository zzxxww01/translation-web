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
    ) -> str:
        """
        通用文本生成（用于四步法的各个步骤）

        Args:
            prompt: 提示词
            response_format: 响应格式，"json" 表示期望 JSON 输出
            temperature: 温度参数
            model: 可选模型选择器（如 flash/pro/preview 或具体模型 id）

        Returns:
            str: 生成的文本
        """
        pass

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

    def understand_section(
        self,
        section_content: str,
        article_theme: str,
        structure_summary: str,
        section_titles: List[str],
        current_index: int
    ) -> Dict[str, Any]:
        """
        理解章节（四步法 Step 1）

        Args:
            section_content: 章节内容
            article_theme: 文章主题
            structure_summary: 结构概述
            section_titles: 所有章节标题
            current_index: 当前章节索引

        Returns:
            Dict: 章节理解结果
        """
        prompt = self._build_understanding_prompt(
            section_content, article_theme, structure_summary,
            section_titles, current_index
        )
        response = self.generate(prompt, response_format="json")
        return self._parse_json_response(response)

    def reflect_on_translation(
        self,
        source_paragraphs: List[str],
        translations: List[str],
        guidelines: List[str],
        terminology: List[Dict]
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
            source_paragraphs, translations, guidelines, terminology
        )
        response = self.generate(prompt, response_format="json")
        return self._parse_json_response(response)

    def refine_translation(
        self,
        source: str,
        current_translation: str,
        issue_type: str,
        description: str,
        suggestion: str
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
            source, current_translation, issue_type, description, suggestion
        )
        return self.generate(prompt, temperature=0.3)

    def prescan_section(
        self,
        section_id: str,
        section_title: str,
        section_content: str,
        existing_terms: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        章节预扫描（方案 C - Phase 1 Step 1）

        使用 Flash 模型快速扫描章节，提取新术语

        Args:
            section_id: 章节 ID
            section_title: 章节标题
            section_content: 章节内容
            existing_terms: 已有术语表 {term: translation}

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

        prompt = self._build_prescan_prompt(
            section_id=section_id,
            section_title=section_title,
            section_content=section_content,
            existing_terms=existing_terms_text
        )
        response = self.generate(prompt, response_format="json", temperature=0.3)
        return self._parse_json_response(response)

    # ============ Prompt Building Methods ============

    def _build_deep_analysis_prompt(self, text: str, sections_outline: str) -> str:
        """构建深度分析 Prompt（方案 C：增加到 30000 字符）"""
        return self.prompt_manager.get("deep_analysis", sections_outline=sections_outline, text=text[:30000])

    def _build_understanding_prompt(
        self,
        section_content: str,
        article_theme: str,
        structure_summary: str,
        section_titles: List[str],
        current_index: int
    ) -> str:
        """构建章节理解 Prompt"""
        titles_text = "\n".join([
            f"{i+1}. {title}" for i, title in enumerate(section_titles)
        ])
        current_title = section_titles[current_index] if current_index < len(section_titles) else ""

        return self.prompt_manager.get(
            "understanding",
            article_theme=article_theme,
            structure_summary=structure_summary,
            titles_text=titles_text,
            current_index=current_index + 1,
            current_title=current_title,
            section_content=section_content[:5000]
        )

    def _build_reflection_prompt(
        self,
        source_paragraphs: List[str],
        translations: List[str],
        guidelines: List[str],
        terminology: List[Dict]
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

        return self.prompt_manager.get(
            "reflection",
            pairs_text=pairs_text,
            guidelines_text=guidelines_text,
            terms_text=terms_text
        )

    def _build_refine_prompt(
        self,
        source: str,
        current_translation: str,
        issue_type: str,
        description: str,
        suggestion: str
    ) -> str:
        """构建润色 Prompt"""
        return self.prompt_manager.get(
            "refine",
            source=source,
            current_translation=current_translation,
            issue_type=issue_type,
            description=description,
            suggestion=suggestion
        )

    def _build_prescan_prompt(
        self,
        section_id: str,
        section_title: str,
        section_content: str,
        existing_terms: str
    ) -> str:
        """构建章节预扫描 Prompt（方案 C 新增）"""
        return self.prompt_manager.get(
            "section_prescan",
            section_id=section_id,
            section_title=section_title,
            section_content=section_content[:8000],
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
