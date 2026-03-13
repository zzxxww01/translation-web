"""
Shared request/response models for confirmation-related routers.
"""

from typing import List, Optional

from pydantic import BaseModel


class ConfirmParagraphRequest(BaseModel):
    translation: str
    version_id: Optional[str] = None
    custom_edit: bool = False


class UpdateTermsRequest(BaseModel):
    changes: List[dict]  # [{term, old_translation, new_translation}]


class ManualAlignRequest(BaseModel):
    ref_index: int
    target_paragraph_id: str


class ImportVersionRequest(BaseModel):
    version_name: str
    markdown_content: str


class RetranslateRequest(BaseModel):
    instruction: Optional[str] = None
    base_version_id: Optional[str] = None
    option_id: Optional[str] = None


class RetranslateOptionResponse(BaseModel):
    id: str
    label: str
    description: str
    instruction: str


RETRANSLATE_OPTIONS = [
    {
        "id": "readable",
        "label": "可读性",
        "description": "消除翻译腔",
        "instruction": (
            "请从句法结构层面重写译文：\n"
            "1. 优先将长句控制在 30 字以内，超长句必须拆分。\n"
            "2. 被动语态改主动。\n"
            "3. 删除不承载逻辑转折的连接词（如无意义的"此外""然而"）。\n"
            "4. 调整为自然中文语序，直接用动词，不要"对……进行……"。\n"
            "5. 连续三个"的"时优先改写句式消除。\n"
            "\n"
            "示例：\n"
            "❌ 此外，该技术对芯片的性能的提升的效果是非常显著的。\n"
            "✅ 这项技术大幅提升了芯片性能。"
        ),
    },
    {
        "id": "idiomatic",
        "label": "更地道",
        "description": "自然流畅表达",
        "instruction": (
            "请从表达层面重写译文：\n"
            "1. 用具体事实代替空泛描述。\n"
            "2. 用简单结构代替复杂绕行。\n"
            "3. 避免同义词循环（同一段内反复用"提升/增强/优化"等近义词凑字）。\n"
            "4. 避免每段都用"首先/其次/最后"等公式化开头。\n"
            "5. 在非正式语境中，避免堆砌"基于""鉴于""旨在"等书面词，改用"根据""考虑到""为了"等自然表达。\n"
            "\n"
            "示例：\n"
            "❌ 基于上述分析，该公司旨在通过技术创新实现业务的全面提升。\n"
            "✅ 根据以上分析，该公司正通过技术创新推动业务增长。"
        ),
    },
    {
        "id": "professional",
        "label": "更专业",
        "description": "科技媒体风格",
        "instruction": (
            "请重写译文以提升专业表达：\n"
            "1. 保留原文观点和判断力度，不要弱化。\n"
            "2. 产品和技术代号保留英文，行业术语和金融术语用中文。\n"
            "3. 删除不承载信息的套话（如"值得注意的是""众所周知"）。\n"
            "4. 数据密集段落适当拆分重组，保持信息密度。\n"
            "5. 参考术语表中已有的译法保持一致。"
        ),
    },
]


_RETRANSLATE_OPTIONS_BY_ID = {opt["id"]: opt for opt in RETRANSLATE_OPTIONS}


def resolve_retranslate_instruction(
    instruction: Optional[str],
    option_id: Optional[str],
) -> str:
    """Resolve the effective retranslate instruction.

    Priority: explicit instruction text > option_id lookup > empty string.
    """
    if instruction and instruction.strip():
        return instruction.strip()
    if option_id:
        option = _RETRANSLATE_OPTIONS_BY_ID.get(option_id)
        if option:
            return option["instruction"]
    return ""
