import json
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from src.agents.deep_analyzer import DeepAnalyzer
from src.core.models import ArticleAnalysis, Paragraph, Section
from src.llm.base import LLMProvider
from src.services.stage_checkpoints import StageCheckpoints, checkpoint_scope, cached_stage, source_identity
from src.api.routers.translate_models import LongformWorkflowStartRequest
from src.llm.business_budget import run_budget
from src.core.efficiency import EfficiencyOptions


class AnalyzerProvider(LLMProvider):
    model_name = 'test-analysis'
    def __init__(self):
        super().__init__(); self.deep_calls = 0; self.role_calls=0; self.fail_roles=True
    def translate(self,*args,**kwargs): return '译文'
    def analyze(self,*args,**kwargs): return {}
    def verify_high_frequency_terms(self,*args,**kwargs): return []
    def check_consistency(self,*args,**kwargs): return {}
    def deep_analyze_document(self,*args,**kwargs):
        self.deep_calls+=1
        return {'theme':'topic','sampled_terms':[]}
    def generate(self, *args, **kwargs):
        self.role_calls+=1
        if self.fail_roles: raise RuntimeError('role outage')
        return json.dumps({'section_roles':{'s1':{'role_in_article':'body'}}})


def test_completed_core_survives_failed_roles_without_caching_incomplete_analysis(tmp_path):
    p=AnalyzerProvider(); section=Section(section_id='s1', title='Title', paragraphs=[Paragraph(id='p',index=0,source='Text')])
    store=StageCheckpoints(tmp_path,'v3')
    def analyze():
        return cached_stage('analysis',source_identity([section]),lambda:DeepAnalyzer(p).analyze([section]),
            decode=ArticleAnalysis.model_validate, cache_if=lambda value:not value.incomplete_stages)
    with checkpoint_scope(store):
        first=analyze()
        assert first.incomplete_stages == ['section_roles']
        p.fail_roles=False
        second=analyze()
        assert not second.incomplete_stages
        third=analyze()
    assert p.deep_calls==1 and p.role_calls==2
    assert third.theme=='topic'
    assert not section.paragraphs[0].has_usable_translation()  # reuse does not require any translated body


def test_fingerprint_excludes_drafts_but_tracks_source_and_structure():
    section=Section(section_id='s',title='t',paragraphs=[Paragraph(id='p',index=0,source='text')])
    before=source_identity([section])
    section.paragraphs[0].add_translation('draft','m')
    section.paragraphs[0].confirm('confirmed')
    assert source_identity([section])==before
    section.paragraphs[0].source='changed'
    assert source_identity([section])!=before


def test_controls_validate_at_public_request_boundary():
    request=LongformWorkflowStartRequest.model_validate({'efficiency':{'model_scope':'draft','prescan_concurrency':2}})
    assert request.efficiency.model_scope=='draft'
    assert request.efficiency.stage_resume is True and request.efficiency.compact_review is False
    with pytest.raises(ValueError): LongformWorkflowStartRequest.model_validate({'efficiency':{'max_run_calls':0}})
    with pytest.raises(ValueError): LongformWorkflowStartRequest.model_validate({'efficiency':{'skip_fidelity_review':True}})
