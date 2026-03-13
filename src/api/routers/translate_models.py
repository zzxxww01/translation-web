"""
Translate router request/response models.
"""

from typing import Optional

from pydantic import BaseModel


class PostTranslateRequest(BaseModel):
    content: str
    preserve_tone: bool = True
    custom_prompt: Optional[str] = None


class PostTranslateResponse(BaseModel):
    translation: str


class GenerateTitleRequest(BaseModel):
    content: str
    instruction: Optional[str] = None


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
    original_text: str
    current_translation: str
    instruction: Optional[str] = None
    option_id: Optional[str] = None
    conversation_history: Optional[list[dict]] = None


class PostOptimizeResponse(BaseModel):
    optimized_translation: str


class FullTranslateRequest(BaseModel):
    pass


class ResolveConflictRequest(BaseModel):
    term: str
    chosen_translation: str
    apply_to_all: bool = True


# Pre-defined post optimization instruction templates
POST_OPTIMIZE_OPTIONS = {
    "readable": (
        "请从读者认知负荷角度优化译文，让信息更容易扫读和理解：\n"
        "1. 一句一事：每句话只承载一个信息点，信息密集处拆成独立短句\n"
        "2. 主语明确：避免连续无主句，让读者立刻知道"谁做了什么"\n"
        "3. 先结论后解释：核心数据或结论放句首，条件和背景放后面\n"
        '4. 消除"的"堆砌：连续三个"的"必须拆句重组'
    ),
    "idiomatic": (
        "请从用词和表达层面优化译文，让中文更自然地道：\n"
        '1. 删连接词：去掉"此外""然而""值得注意的是"，中文靠语义衔接\n'
        '2. 去公式化：不要"尽管……但仍……""展望未来""综上所述"等套路\n'
        "3. 同一概念前后用同一个词，不要同义词循环替换\n"
        '4. 口语化替换：把"基于""鉴于""旨在"换成"根据""考虑到""为了"'
    ),
    "professional": (
        "请从信息密度与精准度角度优化译文：\n"
        "1. 不加不减：不要添加原文没有的修饰语，也不要省略原文的限定条件\n"
        '2. 删口水话：去掉不提供信息的形容词（"突破性""开创性""令人振奋"）和空洞总结\n'
        "3. 零冗余：没有信息量的句子直接删掉\n"
        "4. 数据清晰：一句话超过3个数据点时拆成多句"
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
