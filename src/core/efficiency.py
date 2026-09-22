"""Explicit efficiency controls. No option silently disables fidelity review."""
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal


class EfficiencyOptions(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    stage_resume: bool = True
    prescan_concurrency: int = Field(1, ge=1, le=8)
    compact_review: bool = False
    model_scope: Literal["all", "draft"] = "all"
    profile: str = Field("default", min_length=1, max_length=50)
    max_stage_seconds: float = Field(1800.0, gt=0, le=86400, allow_inf_nan=False)
    max_stage_calls: int = Field(64, ge=1, le=10000)
    max_run_seconds: float = Field(21600.0, gt=0, le=604800, allow_inf_nan=False)
    max_run_calls: int = Field(1024, ge=1, le=100000)
    max_run_estimated_tokens: int | None = Field(None, ge=1)
    # An estimate over the entire rendered prompt, NOT a tokenizer guarantee.
    max_request_input_tokens: int = Field(24000, ge=512, le=2000000)
    reserved_output_tokens: int = Field(8192, ge=256, le=200000)
    max_context_tokens: int | None = Field(None, ge=1024, le=4000000)
