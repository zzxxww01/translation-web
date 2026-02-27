"""
Translation Agent - 重新翻译服务

提供多种重新翻译策略和对比差异计算
"""

from typing import Optional, Dict, Any, List, Tuple
from enum import Enum
from dataclasses import dataclass

from ..core.models import Paragraph
from ..llm.base import LLMProvider
from ..prompts import get_prompt_manager


class RetranslationOption(str, Enum):
    """重新翻译选项"""

    REWRITE = "rewrite"  # 重写（增加流畅性和可读性）
    CONCISE = "concise"  # 更简洁
    PROFESSIONAL = "professional"  # 更专业


@dataclass
class RetranslationResult:
    """重新翻译结果"""

    original_translation: str
    new_translation: str
    diff_data: Dict[str, Any]
    instruction_used: str


class RetranslationService:
    """重新翻译服务"""

    # Prompt模板
    INSTRUCTION_TEMPLATES = {
        RetranslationOption.REWRITE: (
            "请重新组织语言，增加流畅性和可读性。保持准确性的同时，"
            "让译文更自然、更符合中文表达习惯。"
        ),
        RetranslationOption.CONCISE: (
            "请使用更简洁的表达。删除冗余词汇，保留核心信息，使译文更加精炼。"
        ),
        RetranslationOption.PROFESSIONAL: (
            "请使用更专业、严谨的表述。采用学术化或技术化的语言风格，"
            "提升译文的专业度。"
        ),
    }

    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider
        self.prompt_manager = get_prompt_manager()

    def retranslate(
        self,
        source_text: str,
        current_translation: str,
        option: RetranslationOption = RetranslationOption.REWRITE,
        custom_instruction: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> RetranslationResult:
        """
        重新翻译

        Args:
            source_text: 原文
            current_translation: 当前译文
            option: 重译选项
            custom_instruction: 自定义补充说明
            context: 翻译上下文（可选）

        Returns:
            RetranslationResult
        """
        # 构建完整指令
        instruction = self._build_instruction(option, custom_instruction)

        # 构建Prompt
        prompt = self._build_retranslation_prompt(
            source_text, current_translation, instruction, context or {}
        )

        # 调用LLM
        new_translation = self.llm.generate(prompt, temperature=0.7)

        # 清理结果（移除可能的引号等）
        new_translation = self._clean_translation(new_translation)

        # 计算差异
        diff_data = compute_text_diff(current_translation, new_translation)

        return RetranslationResult(
            original_translation=current_translation,
            new_translation=new_translation,
            diff_data=diff_data,
            instruction_used=instruction,
        )

    def _build_instruction(
        self, option: RetranslationOption, custom_instruction: Optional[str]
    ) -> str:
        """构建完整指令"""
        base_instruction = self.INSTRUCTION_TEMPLATES.get(option, "")

        if custom_instruction:
            return f"{base_instruction}\n额外要求：{custom_instruction}"

        return base_instruction

    def _build_retranslation_prompt(
        self, source: str, current: str, instruction: str, context: Dict[str, Any]
    ) -> str:
        """构建重新翻译Prompt"""

        # 构建术语表部分
        glossary_section = ""
        if context.get("glossary"):
            glossary_text = self._format_glossary(context["glossary"])
            glossary_section = f"\n术语参考：\n{glossary_text}"

        # 使用 prompt 模板
        prompt = self.prompt_manager.get(
            "retranslation",
            source=source,
            current=current,
            instruction=instruction,
            glossary_section=glossary_section
        )

        return prompt

    def _format_glossary(self, glossary: List[Dict]) -> str:
        """格式化术语表"""
        lines = []
        for term in glossary[:10]:  # 限制数量
            original = term.get("original", "")
            translation = term.get("translation", "")
            if original and translation:
                lines.append(f"- {original} → {translation}")
        return "\n".join(lines)

    def _clean_translation(self, text: str) -> str:
        """清理翻译结果"""
        # 移除首尾引号
        text = text.strip()
        if (text.startswith('"') and text.endswith('"')) or (
            text.startswith("'") and text.endswith("'")
        ):
            text = text[1:-1]

        # 移除多余空行
        lines = [line for line in text.split("\n") if line.strip()]
        return "\n".join(lines)


def compute_text_diff(text1: str, text2: str) -> Dict[str, Any]:
    """
    计算两个文本的差异

    返回字级别的差异数据，用于前端高亮显示

    Args:
        text1: 原始文本
        text2: 新文本

    Returns:
        {
            "operations": [
                {"type": "equal", "text": "..."},
                {"type": "delete", "text": "..."},
                {"type": "insert", "text": "..."},
            ],
            "change_percentage": 25.5
        }
    """
    try:
        import difflib

        # 使用difflib进行字级别对比
        matcher = difflib.SequenceMatcher(None, text1, text2)

        operations = []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                operations.append({"type": "equal", "text": text1[i1:i2]})
            elif tag == "delete":
                operations.append({"type": "delete", "text": text1[i1:i2]})
            elif tag == "insert":
                operations.append({"type": "insert", "text": text2[j1:j2]})
            elif tag == "replace":
                # 拆分为delete + insert
                operations.append({"type": "delete", "text": text1[i1:i2]})
                operations.append({"type": "insert", "text": text2[j1:j2]})

        # 计算变化百分比
        changes = sum(1 for op in operations if op["type"] != "equal")
        total = len(operations)
        change_percentage = (changes / total * 100) if total > 0 else 0

        return {
            "operations": operations,
            "change_percentage": round(change_percentage, 2),
        }

    except ImportError:
        # difflib不可用时的降级方案
        return {
            "operations": [
                {"type": "delete", "text": text1},
                {"type": "insert", "text": text2},
            ],
            "change_percentage": 100.0,
        }


def compute_word_level_diff(text1: str, text2: str) -> List[Tuple[str, str]]:
    """
    计算词级别差异（用于中文）

    Returns:
        [(tag, text), ...]
        tag: 'equal', 'delete', 'insert'
    """
    # 简化实现：按字符分词
    import difflib

    # 中文按字分词
    words1 = list(text1)
    words2 = list(text2)

    matcher = difflib.SequenceMatcher(None, words1, words2)

    result = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            result.append(("equal", "".join(words1[i1:i2])))
        elif tag == "delete":
            result.append(("delete", "".join(words1[i1:i2])))
        elif tag == "insert":
            result.append(("insert", "".join(words2[j1:j2])))
        elif tag == "replace":
            result.append(("delete", "".join(words1[i1:i2])))
            result.append(("insert", "".join(words2[j1:j2])))

    return result
