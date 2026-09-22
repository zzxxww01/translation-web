import pytest
from src.core.models import Section
from src.core.export_completeness import build_translation_completeness


@pytest.mark.parametrize('name', ['vLLM', 'SGLang', 'CUDA', 'Bedrock', 'Tokenomics', 'OpenAI', 'GPT-4', 'GLM 5.3', 'MiniMax M3', 'DeepSeek V4 Pro 0813', 'Qwen3.5 397B', 'Kimi K2.X', 'Agility Robotics', 'Verne Robotics', 'Sunday Robotics', 'Weave Robotics'])
def test_protected_only_heading_is_not_missing_prose(name):
    section = Section(section_id='s', title=name, title_translation=name, paragraphs=[])
    report = build_translation_completeness([section])
    assert report['is_complete'], report


@pytest.mark.parametrize('heading', [
    'Agility Robotics Builds Robots',
    'How Verne Robotics Works',
    'Weave Robotics is hiring engineers',
])
def test_english_sentence_with_protected_name_still_requires_translation(heading):
    """Company names are exempt as standalone headings, not as English prose."""
    section = Section(section_id='s', title=heading, title_translation=heading, paragraphs=[])
    report = build_translation_completeness([section])
    assert not report['is_complete'], report
    assert report['missing_title_count'] == 1, report
