import asyncio
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from src.services.ordered_prescan import ordered_map
from src.llm.base import LLMProvider
from src.llm.phase_provider import configure_phase_provider
from src.core.efficiency import EfficiencyOptions
from src.services.batch_translation_service import BatchTranslationService
from src.prompts.contracts import validate_review


@pytest.mark.asyncio
async def test_parallel_scans_commit_in_source_order_and_bound_work():
    running = peak = 0
    completions, commits = [], []
    async def scan(i):
        nonlocal running, peak
        running += 1; peak = max(peak, running)
        try:
            await asyncio.sleep(0.02 if i % 2 == 0 else 0.001)
            completions.append(i)
            return i * 10
        finally: running -= 1
    async def commit(i, value): commits.append((i, value))
    assert await ordered_map(range(6), scan, commit, concurrency=2) == [0,10,20,30,40,50]
    assert completions.index(1) < completions.index(0)
    assert commits == [(i,i*10) for i in range(6)]
    assert peak == 2 and running == 0


@pytest.mark.asyncio
async def test_cancellation_and_failure_never_commit_late_results():
    cancelled = False
    committed, finished = [], []
    async def scan(i):
        try:
            await asyncio.sleep(0.01 if i == 0 else 0.1)
            return i
        finally: finished.append(i)
    async def commit(i, result):
        nonlocal cancelled
        committed.append(result)
        cancelled = True
    await ordered_map(range(20), scan, commit, concurrency=3, should_cancel=lambda:cancelled)
    assert committed == [0]
    assert len(finished) <= 4
    committed.clear()
    async def fails(i):
        if i == 0: raise RuntimeError('scan failed')
        return i
    with pytest.raises(RuntimeError): await ordered_map(range(3), fails, commit, concurrency=3)
    assert not committed


class TextProvider(LLMProvider):
    model_name = 'local'
    def __init__(self):
        super().__init__(); self.prompts=[]; self.response='{"new_terms": []}'
    def generate(self, prompt, **kwargs):
        self.prompts.append(prompt); return self.response
    def translate(self, text, context=None, timeout=None): return text
    def analyze(self,text): return {}
    def check_consistency(self,*args,**kwargs): return {}
    def deep_analyze_document(self,*args,**kwargs): return {}
    def verify_high_frequency_terms(self,*args,**kwargs): return []


def test_prescan_filters_unmatched_and_nonprose_terms_but_keeps_candidates():
    p = TextProvider()
    p.response = json.dumps({'new_terms':[{'term':'GPU', 'source_quote':'GPU is used.', 'suggested_translation':'图形处理器'}]})
    result = p.prescan_section('s1','Title','They said so. GPU is used. `CUDA` https://example.com/API',
                              {'AI':'DO_NOT_INCLUDE_AI', 'GPU':'GPU_MATCHED', 'API':'DO_NOT_INCLUDE_URL', 'CUDA':'DO_NOT_INCLUDE_CODE', 'unused':'UNRELATED'})
    prompt=p.prompts[0]
    assert 'GPU_MATCHED' in prompt
    assert not any(v in prompt for v in ['DO_NOT_INCLUDE_AI', 'DO_NOT_INCLUDE_URL', 'DO_NOT_INCLUDE_CODE', 'UNRELATED'])
    assert result['new_terms'][0]['term'] == 'GPU'


def test_compact_review_uses_evidence_contract_and_only_changes_report_shape():
    p=TextProvider()
    p.response = json.dumps({'issues':[{'paragraph_index':0, 'issue_type':'accuracy', 'severity':'high',
        'original_text':'Source', 'translation_text':'译文', 'reason':'Evidence and impact', 'suggestion':'Fix'}]})
    value=p.reflect_on_translation(['Source'],['译文'],[],[],context={'compact_review':True})
    result=validate_review(value,['Source'],['译文'])
    assert result['issues'][0]['description']=='Evidence and impact'
    assert 'reason' not in result['issues'][0]
    assert '不返回评分' in p.prompts[0]
    p.response='{}'
    with pytest.raises(ValueError): validate_review(p.reflect_on_translation(['Source'],['译文'],[],[],context={'compact_review':True}),['Source'],['译文'])


def test_phase_facades_do_not_mutate_shared_client_and_preserve_zero():
    class Provider:
        def __init__(self): self.calls=[]
        def generate(self, prompt, **kwargs): self.calls.append(kwargs); return 'ok'
    p=Provider()
    a=configure_phase_provider(p,{'model':'m','temperature':0,'max_tokens':256})
    b=configure_phase_provider(p,{'model':'m','temperature':0.4,'max_tokens':1024})
    a.generate('a',temperature=0.3)
    b.generate('b',max_tokens=2048)
    p.generate('c')
    assert p.calls[0]['temperature']==0 and p.calls[0]['max_tokens']==256
    assert p.calls[1]['temperature']==0.4 and p.calls[1]['max_tokens']==2048
    assert p.calls[2]=={}
    assert not hasattr(p,'_phase_config')


@pytest.mark.parametrize('scope',['draft','all'])
def test_explicit_override_scope_routes_actual_stages(monkeypatch,scope):
    from src.core.model_config import ModelConfig
    class Provider:
        def __init__(self, alias): self.model_alias=alias; self.model_name='physical-'+alias
        def generate(self, *args, **kwargs): return 'ok'
    service=BatchTranslationService.__new__(BatchTranslationService)
    service.efficiency=EfficiencyOptions(model_scope=scope)
    service.user_model_override='chosen'
    service.llm=Provider('chosen')
    service._phase_provider_cache={}
    configs={'phase0_prescan':{'model':'analysis','temperature':0.2}, 'phase1_draft':{'model':'draft','temperature':0.3}, 'phase2_refine':{'model':'review','temperature':0.1}}
    def config(phase, model_override=None, profile='default'):
        return {'model':model_override,'temperature':0.0} if model_override else configs[phase]
    service.model_config=SimpleNamespace(get_model_for_phase=config)
    monkeypatch.setattr('src.api.utils.llm_factory.create_llm_provider',lambda provider:Provider(provider))
    assert service._get_provider_for_phase('phase1_draft').model_alias=='chosen'
    assert service._get_provider_for_phase('phase2_refine').model_alias==('review' if scope=='draft' else 'chosen')
    assert service._auxiliary_provider().model_alias==('analysis' if scope=='draft' else 'chosen')
    assert service._get_provider_for_phase('phase1_draft') is service._get_provider_for_phase('phase1_draft')


def test_same_physical_model_different_alias_does_not_reuse_wrong_route(monkeypatch):
    service=BatchTranslationService.__new__(BatchTranslationService)
    service.efficiency=EfficiencyOptions(); service.user_model_override=None; service._phase_provider_cache={}
    service.llm=SimpleNamespace(model_alias='old-route', model_name='physical',generate=lambda *a,**kw:'old')
    service.model_config=SimpleNamespace(get_model_for_phase=lambda *a,**kw:{'model':'new-route','temperature':0.0})
    monkeypatch.setattr('src.llm.config_loader.get_config_loader', lambda:SimpleNamespace(get_model_config=lambda _:SimpleNamespace(real_model='physical')))
    created=SimpleNamespace(model_alias='new-route', generate=lambda *a,**kw:'new')
    factory=Mock(return_value=created)
    monkeypatch.setattr('src.api.utils.llm_factory.create_llm_provider',factory)
    assert service._get_provider_for_phase('phase1_draft').generate('test')=='new'
    factory.assert_called_once_with(provider='new-route')
