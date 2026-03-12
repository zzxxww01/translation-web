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
        "id": "fluent",
        "label": "更流畅",
        "description": "让译文更自然流畅，减少机器翻译痕迹",
        "instruction": "请重新翻译这段文字，使其更自然流畅，避免生硬表达，在保留原意的前提下提升可读性。",
    },
    {
        "id": "professional",
        "label": "更专业",
        "description": "使用更专业的术语和行业表达",
        "instruction": "请使用更专业的技术术语与行业表达重新翻译该段落，使其适合专业读者阅读。",
    },
    {
        "id": "concise",
        "label": "更简洁",
        "description": "精简冗余表达，使译文更紧凑",
        "instruction": "请以更简洁的方式翻译该段落，去除冗余表述，同时保留关键信息。",
    },
    {
        "id": "colloquial",
        "label": "更口语化",
        "description": "采用更口语、自然的表达方式",
        "instruction": "请用更口语化、更自然的中文重译该段落，让读者读起来更贴近日常表达。",
    },
    {
        "id": "literal",
        "label": "更忠实原文",
        "description": "尽量贴近原文结构与措辞",
        "instruction": "请更忠实地翻译该段落，尽量保持原文句式与信息细节，避免过度意译。",
    },
    {
        "id": "creative",
        "label": "重新理解后翻译",
        "description": "先重构理解，再给出新的译文表达",
        "instruction": "请先重新理解原文语义，再提供一个全新的译文版本。允许改写表达，但必须准确传达原意。",
    },
]
