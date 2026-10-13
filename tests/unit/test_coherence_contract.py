from src.api.routers.translate_models import resolve_post_optimize_instruction
from src.prompts.editing_options import OPTIONS_BY_ID, POST_OPTIMIZE_OPTIONS


def test_legacy_coherence_option_resolves_canonical_instruction():
    instruction = OPTIONS_BY_ID["coherence"]["instruction"]
    assert instruction
    assert resolve_post_optimize_instruction(None, "coherence") == instruction
    assert resolve_post_optimize_instruction("", "coherence") == instruction
    assert instruction != POST_OPTIMIZE_OPTIONS["readable"]
    assert resolve_post_optimize_instruction("自定义", "coherence") == "自定义"
