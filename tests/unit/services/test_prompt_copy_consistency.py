from src.prompts import get_prompt_manager
from src.services.batch_translation_service import SECTION_TITLE_WHITELIST_RULES

def test_all_longform_surfaces_use_the_same_policy():
    pm = get_prompt_manager()
    policy = pm.get("shared/longform_policy").strip()
    assert SECTION_TITLE_WHITELIST_RULES.strip() == policy
    for name in ("paragraph_translate", "paragraph_retranslate", "section_batch_translate"):
        assert policy in pm.get("longform/translation/" + name)
    assert policy in pm.get("longform/auxiliary/section_title_translate")
