"""
Shared request/response models for confirmation-related routers.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ConfirmParagraphRequest(BaseModel):
    translation: str = Field(..., min_length=1, max_length=50000)
    version_id: Optional[str] = Field(None, max_length=100)
    custom_edit: bool = False


class UpdateTermsRequest(BaseModel):
    changes: List[dict] = Field(..., max_length=100)


class ManualAlignRequest(BaseModel):
    ref_index: int = Field(..., ge=0)
    target_paragraph_id: str = Field(..., min_length=1, max_length=100)


class ImportVersionRequest(BaseModel):
    version_name: str = Field(..., min_length=1, max_length=200)
    markdown_content: str = Field(..., min_length=1, max_length=1000000)


class RetranslateRequest(BaseModel):
    instruction: Optional[str] = Field(None, max_length=2000)
    base_version_id: Optional[str] = Field(None, max_length=100)
    option_id: Optional[str] = Field(None, max_length=100)


class RetranslateOptionResponse(BaseModel):
    id: str
    label: str
    description: str
    instruction: str


from src.prompts.editing_options import EDITING_OPTIONS as RETRANSLATE_OPTIONS


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
