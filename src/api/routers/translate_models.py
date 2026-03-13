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
        "请从句法结构层面优化译文，消除翻译腔：\n"
        "1. 拆长句：超过30字的句子拆成2-3个短句，中文句子控制在15-30字\n"
        "2. 去被动：被动语态一律改为主动表达\n"
        '3. 减连接词：删掉多余的"此外""然而""值得注意的是"，中文靠语义衔接\n'
        "4. 调语序：条件、原因、时间状语放到句首，按中文思维重新组织\n"
        '5. 用动词：把"对……进行……""做出了……"改为直接动词\n'
        '6. 消除"的"堆砌：连续出现三个"的"必须拆句重组'
    ),
    "idiomatic": (
        "请从表达层面优化译文，让中文更地道自然：\n"
        '1. 用具体数据和事实替代空泛描述，删掉"突破性""革命性"等宣传词\n'
        '2. 用简单结构（是/有/能）代替复杂绕行（"作为……的体现""充当……的角色"）\n'
        '3. 不要公式化段落（"尽管……但仍……""展望未来""综上所述"）\n'
        "4. 不要同义词循环替换，同一个概念前后用同一个词\n"
        '5. 模糊归因要么给出具体来源，要么删掉（不要"业界专家普遍认为"）\n'
        '6. 口语化替换：把"基于""鉴于""旨在"换成"根据""考虑到""为了"等自然表达'
    ),
    "professional": (
        "请优化译文的专业表达，使其体现semiAnalysis的分析师水准：\n"
        '1. 保留原文的观点和判断力度，不要弱化成中性表述（"We believe" → "我们认为"，不是"据分析"）\n'
        "2. 使用标准的半导体/科技术语，产品代号保留英文（CoWoS、HBM、EUV），行业术语用中文（晶圆代工、良率、制程节点），金融术语用中文（营收、毛利率、资本支出）\n"
        "3. 删除口水话：去掉不提供信息的形容词和空洞的总结性段落\n"
        '4. 不要宣传腔（"令人兴奋""开创性""无缝集成"），也不要黑话和圈子用语\n'
        "5. 每句话都要有实质内容，没有信息量的句子直接删掉\n"
        '6. 数据密集段落：一句话超过3个数据点拆成多句，金额统一为"亿美元"格式'
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
