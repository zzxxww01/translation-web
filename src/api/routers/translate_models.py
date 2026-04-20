"""
Translate router request/response models.
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator


# 内容长度限制（公网环境防止滥用）
MAX_POST_CONTENT_LENGTH = 10000  # 10K 字符，约 3000 词
MAX_CUSTOM_PROMPT_LENGTH = 2000


class PostTranslateRequest(BaseModel):
    content: str = Field(..., max_length=MAX_POST_CONTENT_LENGTH)
    preserve_tone: bool = True
    custom_prompt: Optional[str] = Field(None, max_length=MAX_CUSTOM_PROMPT_LENGTH)
    model: Optional[str] = None

    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Content cannot be empty")
        if len(v.strip()) < 10:
            raise ValueError("Content too short (minimum 10 characters)")
        return v


class PostTranslateResponse(BaseModel):
    translation: str


class GenerateTitleRequest(BaseModel):
    content: str = Field(..., max_length=MAX_POST_CONTENT_LENGTH)
    instruction: Optional[str] = None
    model: Optional[str] = None

    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Content cannot be empty")
        return v


class GenerateTitleResponse(BaseModel):
    title: str


class ProjectAnalysisResponse(BaseModel):
    summary: str
    notes: list[str]
    key_terms: list[str]


class SectionAnalysisResponse(BaseModel):
    summary: str
    tips: list[str]


class PostOptimizeRequest(BaseModel):
    original_text: str = Field(..., max_length=MAX_POST_CONTENT_LENGTH)
    current_translation: str = Field(..., max_length=MAX_POST_CONTENT_LENGTH)
    instruction: Optional[str] = Field(None, max_length=1000)
    option_id: Optional[str] = None
    conversation_history: Optional[list[dict]] = Field(None, max_length=10)
    model: Optional[str] = None

    @field_validator('conversation_history')
    @classmethod
    def validate_history(cls, v: Optional[list[dict]]) -> Optional[list[dict]]:
        if v is None:
            return v
        if len(v) > 10:
            raise ValueError("Conversation history too long (max 10 messages)")
        for msg in v:
            if not isinstance(msg, dict) or 'role' not in msg or 'content' not in msg:
                raise ValueError("Invalid conversation history format")
        return v


class PostOptimizeResponse(BaseModel):
    optimized_translation: str


class FullTranslateRequest(BaseModel):
    model: Optional[str] = None


class ResolveConflictRequest(BaseModel):
    term: str
    chosen_translation: str
    apply_to_all: bool = True


# Pre-defined post optimization instruction templates.
POST_OPTIMIZE_OPTIONS = {
    "readable": (
        "请从读者认知负荷角度优化译文，让信息更容易扫读和理解：\n"
        "1. 一句一事：每句话只承载一个信息点，信息密集处拆成独立短句。\n"
        "2. 主语明确：避免连续无主句，让读者立刻知道“谁做了什么”。\n"
        "3. 先结论后解释：核心数据或结论放句首，条件和背景放后面。\n"
        "4. 消除“的”堆叠：连续三个“的”必须拆句重组。\n"
        "5. 对中文读者不够自明的缩写，首次出现补成“中文全称（缩写）”，不要裸写造成理解障碍。"
    ),
    "idiomatic": (
        "请从用词和表达层面优化译文，让中文更自然地道：\n"
        "1. 删连接词：去掉“此外”“然而”“值得注意的是”，靠语义衔接。\n"
        "2. 去公式化：不要“尽管……但仍……”“展望未来”“综上所述”等套话。\n"
        "3. 同一概念前后使用同一个词，避免同义词循环替换。\n"
        "4. 口语化替换：把“基于”“鉴于”“旨在”改成“根据”“考虑到”“为了”。\n"
        "5. 对 went viral、rant、slam、blast 这类表达，不要字面直译，要改成中文社交媒体真正会这样说的话。"
    ),
    "professional": (
        "请从信息密度与精准度角度优化译文：\n"
        "1. 不加不减：不要添加原文没有的修饰，也不要省略原文限定条件。\n"
        "2. 删口水话：去掉不提供信息的形容词（如“突破性”“开创性”“令人振奋”）和空洞总结。\n"
        "3. 零冗余：没有信息量的句子直接删除。\n"
        "4. 数据清晰：一句话超过 3 个数据点时拆成多句。\n"
        "5. 如果原文存在明显的因果或态度递进关系，中文必须把链条写清楚，不能只留下抽象结论。"
    ),
}


def resolve_post_optimize_instruction(
    instruction: Optional[str], option_id: Optional[str]
) -> str:
    """
    Resolve optimization instruction. Prioritizes custom instruction if provided,
    otherwise looks up the option_id.
    """
    if instruction and instruction.strip():
        return instruction.strip()

    if option_id and option_id in POST_OPTIMIZE_OPTIONS:
        return POST_OPTIMIZE_OPTIONS[option_id]

    return ""
