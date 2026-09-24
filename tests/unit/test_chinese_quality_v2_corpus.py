"""Validate the corpus, not model quality. Live generations are explicitly opt-in."""
import json
import os
from pathlib import Path
import re
import pytest

CASES = json.loads((Path(__file__).parents[1] / 'chinese_quality_v2_cases.json').read_text(encoding='utf-8'))['cases']

def normalize(text):
    return re.sub(r'\s+', '', text)

@pytest.mark.parametrize('case', CASES, ids=lambda case: case['id'])
def test_development_case_is_internally_consistent(case):
    assert case['source'] and case['reference_translation']
    assert case['synthetic'] is True
    assert case['semantic_checks']
    assert case['reference_translation'] != case['reject_example']
    for fragment in case['preserve']:
        assert normalize(fragment) in normalize(case['reference_translation'])


def test_case_ids_unique_and_cover_both_sentence_extremes():
    assert len({c['id'] for c in CASES}) == len(CASES) == 40
    categories={case['category'] for case in CASES}
    assert {'自然把字句', '碎句合并', '长句拆分', '长定语', '句间衔接', '不必修改'} <= categories


@pytest.mark.skipif(os.getenv('RUN_LLM_TESTS', '').lower() not in {'1', 'true', 'yes'}, reason='需显式开启真实模型验收')
def test_live_chinese_generations(tmp_path):
    # Use the production prompt manager and task routing. This only checks protected
    # strings; all semantic_checks still require human blind review of saved outputs.
    from src.prompts import get_prompt_manager
    from src.api.utils.llm_factory import generate_with_fallback
    from src.api.utils.glossary import build_glossary_context
    outputs=[]
    for case in CASES:
        # Format-token fixtures belong to the paragraph path, not plain social posts.
        if case['category'] == '格式语义':
            from src.prompts.task_builders import paragraph_prompt
            prompt=paragraph_prompt(case['source'], {})
            task='longform'
        else:
            prompt=get_prompt_manager().render('post_translation', text=case['source'], dynamic_sections=build_glossary_context(case['source']))
            task='post'
        output=generate_with_fallback(prompt,task_type=task)
        outputs.append({**case,'output':output})
    path=tmp_path/'live-generations.json'
    path.write_text(json.dumps(outputs,ensure_ascii=False,indent=2),encoding='utf-8')
    failures=[row['id'] for row in outputs for fragment in row['preserve'] if normalize(fragment) not in normalize(row['output'])]
    assert not failures, f'保护内容缺失: {failures}; 完整输出 {path}'
