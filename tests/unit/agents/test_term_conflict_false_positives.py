"""A term kept in English (empty stored translation) must not conflict with a suggestion of itself.

A full-article run raised 44 such "conflicts" (CUDA, GB200 NVL72, InferenceMAX vs InferenceMAX™ ...),
each one a confirmation the user had to click through.
"""
import pytest

from src.agents.context_manager import LayeredContextManager, _same_rendering
from src.core.models import EnhancedTerm, PrescanTerm


@pytest.mark.parametrize("existing, suggested, term, same", [
    (None, "CUDA", "CUDA", True),
    ("", "GB200 NVL72", "GB200 NVL72", True),
    ("InferenceMAX", "InferenceMAX™", "InferenceMAX", True),
    ("帕累托前沿", "帕累托 前沿", "Pareto frontier", True),
    ("预填充", "预充填", "prefill", False),
    (None, "库达", "CUDA", False),
])
def test_same_rendering(existing, suggested, term, same):
    assert _same_rendering(existing, suggested, term) is same


def test_prescan_suggesting_the_kept_term_itself_is_not_a_conflict():
    ctx = LayeredContextManager()
    ctx.terminology_version.add_term(EnhancedTerm(term="CUDA", translation=None, context_meaning="NVIDIA 编程平台"))
    ctx.terminology_version.add_term(EnhancedTerm(term="prefill", translation="预填充", context_meaning="推理阶段"))
    conflicts = ctx.add_terms_from_prescan([
        PrescanTerm(term="CUDA", suggested_translation="CUDA"),
        PrescanTerm(term="prefill", suggested_translation="预充填"),
    ], "s1")
    assert [c.term for c in conflicts] == ["prefill"]
