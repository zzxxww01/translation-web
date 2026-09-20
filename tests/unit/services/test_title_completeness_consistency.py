import pytest
from src.core.models import Section
from src.core.export_completeness import build_translation_completeness


@pytest.mark.parametrize('name', ['vLLM', 'SGLang', 'CUDA', 'Bedrock', 'Tokenomics', 'OpenAI', 'GPT-4', 'GLM 5.3', 'MiniMax M3', 'DeepSeek V4 Pro 0813', 'Qwen3.5 397B', 'Kimi K2.X'])
def test_protected_only_heading_is_not_missing_prose(name):
    section = Section(section_id='s', title=name, title_translation=name, paragraphs=[])
    report = build_translation_completeness([section])
    assert report['is_complete'], report
