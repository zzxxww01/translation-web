from types import SimpleNamespace
from unittest.mock import Mock
from threading import Lock, Event
import json
import time
from pathlib import Path

import pytest
from src.config.efficiency import EfficiencyOptions
from src.services.batch_translation_service import BatchTranslationService
from src.agents.four_step_translator import FourStepTranslator
from src.agents.context_manager import LayeredContextManager
from src.core.models import Section, Paragraph, SectionPrescanResult, EnhancedTerm, ProjectMeta
from src.core.project_repository import ProjectRepository, SectionDataError
from src.services.work_checkpoints import WorkCheckpointStore, checkpoint_scope
from src.llm.base import LLMProvider
from src.llm.work_budget import WorkBudgetExceeded
from src.core.model_config import ModelConfig


def make_service(n=6):
    service=BatchTranslationService.__new__(BatchTranslationService)
    service.efficiency=EfficiencyOptions(prescan_concurrency=3)
    service.context_manager=LayeredContextManager()
    service.context_manager.add_terms_from_analysis([EnhancedTerm(term='GPU',translation='GPU')])
    service.translator=FourStepTranslator(object(),service.context_manager)
    service._is_cancelled=lambda _:False
    service._get_provider_for_phase=lambda phase:SimpleNamespace(model_name='prescan')
    service._touch_progress=Mock();service._persist_section_artifact=Mock()
    project=SimpleNamespace(sections=[Section(section_id=f's{i}',title=f'S{i}',paragraphs=[Paragraph(id=f'p{i}',index=0,source=f'GPU text {i}')]) for i in range(n)])
    return service,project


@pytest.mark.asyncio
async def test_prescan_parallel_network_and_ordered_commits(tmp_path):
    service,project=make_service()
    seen=[];applied=[];finished=[];state={'active':0,'max':0};lock=Lock();later_finished=Event()
    def scan(section,existing_terms=None,provider=None):
        with lock:
            state['active']+=1;state['max']=max(state['max'],state['active'])
            seen.append(dict(existing_terms))
        try:
            if section.section_id=='s0':
                assert later_finished.wait(5), 'prescan was serialized'
            else:
                time.sleep(0.01)
            finished.append(section.section_id)
            if section.section_id=='s1': later_finished.set()
            return SectionPrescanResult(section_id=section.section_id,new_terms=[],term_usages={},scan_coverage=1)
        finally:
            with lock:state['active']-=1
    service.translator.scan_section_terms=scan
    def apply(result,**kw):
        applied.append(result.section_id)
        service.context_manager.add_terms_from_analysis([EnhancedTerm(term='Added'+result.section_id,translation='new')])
    service.translator.apply_section_prescan=apply
    cache=WorkCheckpointStore(tmp_path/'cache')
    with checkpoint_scope(cache):
        await service._prescan_all_sections('project',project,tmp_path,SimpleNamespace(errors=[]),None)
    assert 1 < state['max'] <= 3 and finished[0]!='s0'
    assert applied==[f's{i}' for i in range(6)]
    assert all(terms=={'gpu':'GPU'} for terms in seen)
    assert cache.writes==6


@pytest.mark.asyncio
async def test_failed_prescan_is_not_cached_or_applied(tmp_path):
    service,project=make_service(2)
    def scan(section,**kw):
        if section.section_id=='s0':raise RuntimeError('no result')
        return SectionPrescanResult(section_id=section.section_id)
    service.translator.scan_section_terms=scan
    applied=[];service.translator.apply_section_prescan=lambda result,**kw:applied.append(result.section_id)
    cache=WorkCheckpointStore(tmp_path/'cache');progress=SimpleNamespace(errors=[])
    with checkpoint_scope(cache):
        await service._prescan_all_sections('p',project,tmp_path,progress,None)
    assert applied==['s1'] and cache.writes==1
    assert progress.errors==[{'type':'prescan_incomplete','section_id':'s0'}]


@pytest.mark.asyncio
async def test_budget_pause_stops_ordered_prescan_commit(tmp_path):
    service,project=make_service(4)
    def scan(section,**kw):
        if section.section_id=='s0':raise WorkBudgetExceeded('run')
        time.sleep(0.03)
        return SectionPrescanResult(section_id=section.section_id)
    service.translator.scan_section_terms=scan
    applied=[];service.translator.apply_section_prescan=lambda result,**kw:applied.append(result.section_id)
    with pytest.raises(WorkBudgetExceeded):
        await service._prescan_all_sections('p',project,tmp_path,SimpleNamespace(errors=[]),None)
    assert applied==[]


def test_prescan_payload_only_includes_locally_matched_terms():
    class Fake(LLMProvider):
        def __init__(self):self.terms=[]
        def generate(self,*a,**kw):return '{"new_terms": []}'
        def translate(self,*a,**kw):raise NotImplementedError
        def analyze(self,*a,**kw):raise NotImplementedError
        def check_consistency(self,*a,**kw):raise NotImplementedError
        def deep_analyze_document(self,*a,**kw):raise NotImplementedError
        def verify_high_frequency_terms(self,*a,**kw):raise NotImplementedError
        def _build_prescan_prompt(self,**kwargs):self.terms.append(json.loads(kwargs['existing_terms']));return 'prompt'
    provider=Fake()
    provider.prescan_section('s','t','The GPU was said to run.',{'GPU':'图形处理器','AI':'人工智能','Unrelated':'无关'})
    assert provider.terms==[{'GPU':'图形处理器'}]


def repository(tmp_path):
    reads=[]
    def read(path):reads.append(path);return json.loads(path.read_text())
    repo=ProjectRepository(project_dir_resolver=lambda project:tmp_path/project,read_json=read,
        write_json=lambda p,d:p.write_text(json.dumps(d)),write_text=lambda p,s:p.write_text(s),
        get_project=lambda _:None,render_source_block_markdown=lambda ps:'\n'.join(p.source for p in ps),
        render_markdown_line=lambda typ,s:s,best_translation_text=lambda p,**kw:p.best_translation_text(**kw))
    section=Section(section_id='s',title='title',paragraphs=[Paragraph(id='p',index=0,source='Original')])
    folder=tmp_path/'project'/'sections'/'s';folder.mkdir(parents=True)
    path=folder/'meta.json';path.write_text(section.model_dump_json())
    return repo,reads,path


def test_parsed_section_cache_avoids_reparse_and_returns_independent_copies(tmp_path):
    repo,reads,path=repository(tmp_path)
    a=repo.load_section('project','s');a.paragraphs[0].source='local edit'
    b=repo.load_section('project','s')
    assert b.paragraphs[0].source=='Original' and len(reads)==1


def test_parsed_cache_detects_atomic_same_length_replacement(tmp_path):
    repo,reads,path=repository(tmp_path);repo.load_section('project','s')
    content=path.read_text().replace('Original','Changed!');replacement=path.with_suffix('.new')
    replacement.write_text(content);replacement.replace(path)
    assert repo.load_section('project','s').paragraphs[0].source=='Changed!'
    assert len(reads)==2


def test_damaged_replacement_never_reuses_old_success(tmp_path):
    repo,reads,path=repository(tmp_path);repo.load_section('project','s')
    path.write_text('{broken')
    with pytest.raises(SectionDataError):repo.load_section('project','s')
    assert path.read_text()=='{broken'


@pytest.mark.parametrize('scope,phase,expected',[('all','phase0_prescan','selected'),('all','phase2_refine','selected'),
    ('draft','phase1_draft','selected'),('draft','phase0_prescan','phase0'),('draft','phase2_refine','phase2')])
def test_model_scope_routes_to_selected_or_configured_phase(monkeypatch,scope,phase,expected):
    service=BatchTranslationService.__new__(BatchTranslationService)
    service.user_model_override='selected';service.model_scope=scope;service.model_profile='default'
    service._phase_provider_cache={};service.llm=SimpleNamespace(model_name='selected')
    class Config:
        def get_model_for_phase(self,phase,**kw):return {'model':kw.get('model_override') or phase.split('_')[0], 'temperature':0.3}
    service.model_config=Config()
    monkeypatch.setattr('src.api.utils.llm_factory.create_llm_provider',lambda provider:SimpleNamespace(model_name=provider))
    assert service._get_provider_for_phase(phase).model_name==expected


def test_api_efficiency_settings_are_explicit_and_validated():
    from src.api.routers.translate_models import LongformWorkflowStartRequest
    data=LongformWorkflowStartRequest(model='my-model',model_scope='draft',efficiency={'compact_review':True,'prescan_concurrency':2})
    assert data.efficiency.compact_review is True and data.efficiency.resume_stages is True
    with pytest.raises(ValueError):LongformWorkflowStartRequest(efficiency={'max_stage_calls':0})
    with pytest.raises(ValueError):LongformWorkflowStartRequest(model_scope='cheap')
