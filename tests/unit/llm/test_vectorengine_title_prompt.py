"""Exercise the real title template without making an upstream call."""
from src.llm.vectorengine import VectorEngineProvider
from src.prompts import get_prompt_manager


def test_section_title_renders_glossary_before_generate():
    provider = object.__new__(VectorEngineProvider)
    provider.prompt_manager = get_prompt_manager()
    prompts = []
    provider.generate = lambda prompt, **kwargs: prompts.append(prompt) or '我们如何衡量'
    result = provider.translate_section_title('How we measured', context={'glossary_block': 'harness → 模型集成层'})
    assert result == '我们如何衡量'
    assert 'harness → 模型集成层' in prompts[0]


def test_section_title_without_context_still_renders():
    provider = object.__new__(VectorEngineProvider)
    provider.prompt_manager = get_prompt_manager()
    provider.generate = lambda prompt, **kwargs: '引言'
    assert provider.translate_section_title('Introduction') == '引言'
