"""Offline contracts and orchestration regressions. No paid model calls."""
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, AsyncMock
import pytest

from src.prompts import PromptManager, get_prompt_manager, prompt_bundle_scope
from src.prompts.contracts import PromptContractError, object_response, parse_json, parse_title_lines, text_version, translation_items, validate_review
from src.prompts.task_registry import list_tasks
from src.prompts.editing_options import POST_OPTIMIZE_OPTIONS, history_option_summary, OPTION_VERSION
from src.llm.base import LLMProvider
from src.llm.gemini import GeminiProvider
from src.llm.vectorengine import VectorEngineProvider
from src.agents.context_manager import LayeredContextManager
from src.agents.four_step_translator import FourStepTranslator
from src.agents.quality_gate import QualityGate
from src.core.format_tokens import TranslationPayload, validate_tokenized_text
from src.core.models import Paragraph, Section, SectionUnderstanding, ReflectionResult, TranslationIssue, InlineElement, Glossary, GlossaryTerm, TranslationStrategy, ElementType
from src.core.glossary_prompt import build_annotation_plan, build_term_usage_from_project
from src.services.memory_service import TranslationMemoryService
from src.services.memory_candidates import RuleCandidates
from src.services.translation_artifact_service import TranslationArtifactService

TASKS = list_tasks()

@pytest.mark.parametrize('task', TASKS, ids=lambda task: task['task_id'])
def test_every_task_renders_complete_shared_contract(task):
    pm = get_prompt_manager()
    # Format strings retain legacy numeric score placeholders in the refine template.
    fields = {key: (8.0 if key.endswith('_score') else f'SENTINEL_{key}') for key in task['variables']}
    result = pm.render(task['task_id'], **fields)
    assert result.strip()
    assert '[[include:' not in result
    for key in fields:
        if not key.endswith('_score'):
            assert f'SENTINEL_{key}' in result


def test_render_rejects_unused_and_missing_fields():
    pm = get_prompt_manager()
    with pytest.raises(ValueError, match='unused'):
        pm.render('tools_translate_en2cn', text='hello', ignored_context='x')
    with pytest.raises(ValueError, match='missing'):
        pm.render('tools_translate_en2cn')


def test_source_braces_are_not_formatted_twice():
    source = '{text} {instruction} {{a: 1}} [[include:shared/fidelity]]'
    result = get_prompt_manager().render('tools_translate_en2cn', text=source)
    assert source in result  # injected source is data, not template code


def test_include_cycle_is_rejected(tmp_path):
    (tmp_path / 'a.txt').write_text('[[include:b]]')
    (tmp_path / 'b.txt').write_text('[[include:a]]')
    with pytest.raises(ValueError, match='cycle'):
        PromptManager(str(tmp_path))


def test_missing_include_is_rejected(tmp_path):
    (tmp_path / 'a.txt').write_text('[[include:missing]]')
    with pytest.raises(KeyError):
        PromptManager(str(tmp_path))


def test_run_pins_templates_through_threads(monkeypatch):
    global_pm = get_prompt_manager()
    original = global_pm.get('tools_translate_en2cn', text='SOURCE')
    with prompt_bundle_scope() as frozen:
        monkeypatch.setitem(global_pm._templates, 'tools_translate_en2cn', 'changed {text}')
        assert global_pm.get('tools_translate_en2cn', text='SOURCE') == original
        ctx = copy_context()
        with ThreadPoolExecutor(max_workers=1) as pool:
            actual = pool.submit(ctx.run, lambda: get_prompt_manager().get('tools_translate_en2cn', text='SOURCE')).result()
        assert actual == original
        assert frozen is not global_pm


def test_incompatible_resume_is_rejected():
    with pytest.raises(ValueError, match='changed'):
        with prompt_bundle_scope({'digest': 'old'}):
            pytest.fail('must not run')


def test_snapshot_roundtrip_pins_current_version(tmp_path):
    with prompt_bundle_scope() as pm:
        run_id, path = TranslationArtifactService(tmp_path).create_run_artifact_dir('p')
        snapshot = json.loads((path / 'prompt-bundle.json').read_text())
        assert snapshot['digest'] == pm.snapshot()['digest']
        assert run_id == path.name
    with prompt_bundle_scope(snapshot):
        assert get_prompt_manager().snapshot()['digest'] == snapshot['digest']


@pytest.mark.parametrize('bad', [
    '', 'not json', '{"issues": [', '{"issues": [], "issues": []}',
    '{"score": NaN}', '{"a": 1}\n{"b": 2}',
])
def test_invalid_or_ambiguous_json_is_not_a_clean_result(bad):
    with pytest.raises(PromptContractError):
        object_response(bad)


def test_complete_json_wrapper_is_accepted():
    assert object_response('```json\n{"issues": []}\n```', ('issues',)) == {'issues': []}


@pytest.mark.parametrize('raw', [
    [{'id':'p1','translation':'a'},{'id':'p1','translation':'b'}],
    [{'id':'foreign','translation':'a'}],
    ['positional output'], [{'id':1,'translation':'a'}], [{'id':'p1','translation':None}],
])
def test_translations_reject_unusable_identity(raw):
    with pytest.raises(PromptContractError):
        translation_items({'translations':raw}, ['p1','p2'])


def test_missing_item_falls_back_by_id_not_array_position():
    assert translation_items({'translations':[{'id':'p2','translation':'second'}]}, ['p1','p2']) == [{'id':'p2','translation':'second'}]


def test_translation_reorder_preserves_identity():
    raw = [{'id':'p2','translation':'second'}, {'id':'p1','translation':'first'}]
    assert [r['translation'] for r in translation_items(raw, ['p1','p2'])] == ['first','second']


def _provider(cls):
    provider = object.__new__(cls)
    LLMProvider.__init__(provider)
    provider.generate = Mock(return_value='{"translations": []}')
    return provider


@pytest.mark.parametrize('task', ['paragraph','section','title','section_title','consistency','analysis','repair'])
def test_provider_business_prompt_parity(task):
    a, b = _provider(GeminiProvider), _provider(VectorEngineProvider)
    context = {'article_title':'TITLE_SENTINEL','article_theme':'THEME_SENTINEL','article_structure':'STRUCTURE_SENTINEL',
               'target_audience':'AUDIENCE_SENTINEL','translation_voice':'VOICE_SENTINEL',
               'section_context':{'role':'ROLE_SENTINEL'}, 'previous_translation':'PREVIOUS_SENTINEL',
               'glossary':[], 'previous_paragraphs':[], 'next_preview':['NEXT_SENTINEL']}
    if task == 'paragraph':
        pa, pb = a._build_translation_prompt('SOURCE', context), b._build_translation_prompt('SOURCE', context)
        for word in ('THEME_SENTINEL','STRUCTURE_SENTINEL','AUDIENCE_SENTINEL','VOICE_SENTINEL','ROLE_SENTINEL','PREVIOUS_SENTINEL'):
            assert word in pa
    elif task == 'section':
        pa, pb = a._build_batch_translation_prompt('[p1] SOURCE','S',context,['p1']), b._build_batch_translation_prompt('[p1] SOURCE','S',context,['p1'])
    else:
        for provider in (a,b):
            if task == 'title':
                provider.generate.return_value = '标题：主体：细节\n副标题：'
                assert provider.translate_title('Subject: detail',context)['title'] == '主体：细节'
            elif task == 'section_title':
                provider.generate.return_value='章节'
                provider.translate_section_title('Section',context)
            elif task == 'analysis':
                provider.generate.return_value='{"terms": [], "style": {}, "summary": "s"}'
                provider.analyze('SOURCE')
            elif task == 'consistency':
                provider.generate.return_value='{"issues": []}'
                provider.check_consistency([{'source':'SOURCE','translation':'译文'}],{})
            else:
                provider.generate.return_value='[[[LINK_1|链接]]]'
                provider.repair_format_tokens('[[[LINK_1|link]]]','链接',[{'id':'LINK_1','type':'link','text':'link'}],['missing'])
        pa,pb=a.generate.call_args.args[0],b.generate.call_args.args[0]
    assert pa == pb


@pytest.mark.parametrize('text,expected', [
    ('标题：主体：细节', '主体：细节'), ('标题: Subject: details', 'Subject: details'),
    ('标题：2026: 供需：展望', '2026: 供需：展望'),
])
def test_title_inner_colons_survive(text, expected):
    assert parse_title_lines(text)['title'] == expected


def test_correction_alignment_rejects_duplicate_and_bare_results():
    provider = _provider(VectorEngineProvider)
    pairs=[{'translation':'old0'},{'translation':'old1'}]
    assert provider._align_polished_batch([{'index':1,'translation':'new1'}],pairs) == ['old0','new1']
    for bad in (['a','b'],[{'index':0,'translation':'a'},{'index':0,'translation':'b'}],[{'index':True,'translation':'b'}]):
        with pytest.raises(PromptContractError):
            provider._align_polished_batch(bad,pairs)


def _section():
    return Section(section_id='s',title='Test',paragraphs=[Paragraph(id='p1',index=0,source='Latency decreased, but memory did not change.'),Paragraph(id='p2',index=1,source='Bandwidth stayed the same.')])


def _finding(severity='high', kind='readability'):
    return TranslationIssue(paragraph_index=0,issue_type=kind,severity=severity,priority='P1',original_text='but',translation_text='内存没有变化',description='转折关系未表达',suggestion='恢复转折关系')


def _review(issues=(), score=9):
    return ReflectionResult(issues=list(issues),overall_score=score,accuracy_score=score,fluency_score=score,readability_score=score)


def _translator(reviews, candidate=None):
    tr=FourStepTranslator(SimpleNamespace(),LayeredContextManager())
    tr._step_understand=Mock(return_value=SectionUnderstanding())
    tr._translate_batch=Mock(return_value=[TranslationPayload(text='延迟降低了。内存没有变化。'),TranslationPayload(text='带宽不变。')])
    tr._step_reflect=Mock(side_effect=reviews)
    tr._step_refine_and_polish=Mock(return_value=candidate or [TranslationPayload(text='延迟降低了，但内存没有变化。'),TranslationPayload(text='带宽不变。')])
    return tr


def test_revision_gets_new_review_and_correct_hash():
    tr=_translator([_review([_finding()]),_review()]);section=_section()
    result=tr.translate_section(section,[section])
    assert tr._step_reflect.call_count == 2
    assert len(result.review_history)==2
    assert result.review_history[0]['version'] != result.review_history[1]['version']
    assert result.reflection.reviewed_version == text_version([p.source for p in section.paragraphs],result.translations)
    assert result.assessment.passed
    assert tr._step_refine_and_polish.call_args.kwargs['polish_all'] is False


def test_low_score_without_finding_does_not_rewrite():
    tr=_translator([_review(score=3)]);section=_section()
    result=tr.translate_section(section,[section])
    tr._step_refine_and_polish.assert_not_called()
    assert tr._step_reflect.call_count==1 and not result.revision_attempted


def test_noop_preserves_review_version():
    candidate=[TranslationPayload(text='延迟降低了。内存没有变化。'),TranslationPayload(text='带宽不变。')]
    tr=_translator([_review([_finding()])],candidate);s=_section()
    result=tr.translate_section(s,[s])
    assert tr._step_reflect.call_count==1
    assert not result.assessment.passed


def test_failed_verification_returns_matching_draft_payload():
    tr=_translator([_review([_finding()]),RuntimeError('verify unavailable')]);s=_section()
    result=tr.translate_section(s,[s])
    assert result.degraded
    assert result.translations==result.draft_translations
    assert [p['text'] for p in result.translation_outputs]==result.draft_translations
    assert result.assessment is None or not result.assessment.passed


def test_invalid_revision_tokens_do_not_enter_review():
    candidate=[TranslationPayload(text='bad',format_issues=['Missing token']),TranslationPayload(text='带宽不变。')]
    tr=_translator([_review([_finding()])],candidate);s=_section()
    result=tr.translate_section(s,[s])
    assert result.degraded and result.translations==result.draft_translations
    assert tr._step_reflect.call_count==1


def test_more_serious_errors_roll_back_revision():
    tr=_translator([_review([_finding()]),_review([_finding(),_finding('critical','accuracy')])]);s=_section()
    result=tr.translate_section(s,[s])
    assert result.degraded and result.translations==result.draft_translations
    assert not result.assessment.passed


@pytest.mark.parametrize('kind,severity,blocked', [('formatting','critical',True),('tone','low',False),('accuracy','high',True),('readability','medium',False)])
def test_gate_uses_severity_not_category(kind,severity,blocked):
    s=_section();texts=['译文','译文2'];r=_review([_finding(severity,kind)])
    r.reviewed_version=text_version([p.source for p in s.paragraphs],texts)
    assert QualityGate().assess(s,texts,r).passed is (not blocked)


def test_gate_rejects_old_version_and_partial_coverage():
    s=_section();r=_review();r.reviewed_version='stale'
    assert not QualityGate().assess(s,['a','b'],r).passed
    r.reviewed_version='';r.coverage=.5
    assert not QualityGate().assess(s,['a','b'],r).passed


def test_review_counts_derived_and_quote_verified():
    issue={'paragraph_index':0,'severity':'high','original_text':'but','translation_text':'内存','description':'缺转折','suggestion':'补但'}
    good=validate_review({'issues':[issue],'high_issues_count':0}, ['X but Y'], ['内存'])
    assert good['high_issues_count']==1 and good['issues'][0]['priority']=='P1'
    for changes in ({'original_text':'fabricated'}, {'paragraph_index':True}, {'severity':'guess'}):
        with pytest.raises(PromptContractError):
            validate_review({'issues':[dict(issue,**changes)]},['X but Y'],['内存'])


def test_format_tokens_may_move_but_code_cannot_change():
    elements=[InlineElement(type='link',text='A',start=0,end=1,href='https://example.org/a'),InlineElement(type='strong',text='B',start=2,end=3)]
    assert validate_tokenized_text('[[[STRONG_1|乙]]] 和 [[[LINK_1|甲]]]',elements)==[]
    code=[InlineElement(type='code',text='f(x)',start=0,end=4)]
    assert validate_tokenized_text('[[[CODE_1|f(y)]]]',code)
    assert validate_tokenized_text('[[[LINK_7|invented]]]',[])


def test_annotation_source_order_includes_unfinished_body_not_headings():
    term=GlossaryTerm(original='CPO',translation='共封装光学',strategy=TranslationStrategy.FIRST_ANNOTATE)
    sections=[Section(section_id='s1',title='CPO',paragraphs=[Paragraph(id='h',index=0,source='CPO',element_type=ElementType.H3),Paragraph(id='a',index=1,source='CPO optics')]),Section(section_id='s2',title='Later',paragraphs=[Paragraph(id='b',index=0,source='CPO link')])]
    assert build_annotation_plan(sections,[term],'s2',['b'])['cpo']['paragraph_id']=='a'
    assert build_term_usage_from_project(sections,Glossary(terms=[term]),'s1','a')=={}
    assert 'cpo' in build_term_usage_from_project(sections,Glossary(terms=[term]),'s2','b')


@pytest.mark.asyncio
async def test_model_rules_pending_until_explicit_approval(tmp_path,monkeypatch):
    import src.services.memory_service as module
    monkeypatch.setattr(module,'GLOBAL_MEMORY_PATH',tmp_path/'global_memory.md')
    service=TranslationMemoryService()
    service._extract_rules=AsyncMock(return_value=['条件与结论要紧密衔接，避免碎句。'])
    await service.process_retranslation_instruction('理顺关系','source','旧译文很长但断裂','新的自然译文')
    assert service.get_all_rules()==[]
    rows=service.get_rule_candidates();assert len(rows)==1 and rows[0]['status']=='pending'
    service.decide_rule_candidate(rows[0]['id'],'approve')
    assert service.get_all_rules()==['条件与结论要紧密衔接，避免碎句。']
    service.decide_rule_candidate(rows[0]['id'],'approve')
    assert len(service.get_all_rules())==1


def test_reject_rule_never_activates_and_duplicate_dedupes(tmp_path):
    store=RuleCandidates(tmp_path/'global_memory.md');callback=Mock()
    rows=store.add(['test'],'model_reflection',{'source':'text'})
    assert store.add(['test'],'model_reflection',{'source':'text'})==[]
    store.decide(rows[0]['id'],'reject',callback)
    callback.assert_not_called()
    with pytest.raises(ValueError):
        store.decide(rows[0]['id'],'approve',callback)


def test_option_history_does_not_reinstate_legacy_ban():
    assert '旧版' in history_option_summary('idiomatic')
    assert '当前要求优先' in history_option_summary('idiomatic',OPTION_VERSION)
    assert '删连接词' not in POST_OPTIMIZE_OPTIONS['idiomatic']


def test_no_heuristic_person_or_sentence_style_error():
    from src.agents.consistency_reviewer import ConsistencyReviewer
    reviewer=ConsistencyReviewer(SimpleNamespace())
    assert reviewer._check_style_consistency_enhanced([],{'s':['我们认为该模型表现不错。但这取决于带宽。']})[0]==[]


def test_final_review_does_not_drop_missing_evidence():
    from src.agents.quality_report_generator import QualityReportGenerator
    gen=QualityReportGenerator(SimpleNamespace())
    with pytest.raises(ValueError):
        gen._locate_issues([{'description':'problem'}],{'s':['text']})
    with pytest.raises(ValueError):
        gen._locate_issues([{'section_id':'s','paragraph_index':0,'problematic_sentence':'invented'}],{'s':['text']})
