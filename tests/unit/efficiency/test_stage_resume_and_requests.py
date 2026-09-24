"""Stage crash recovery, quality proof and full-request split integration."""
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from src.agents.context_manager import LayeredContextManager
from src.agents.four_step_translator import FourStepTranslator
from src.core.models import Paragraph, Section, ArticleAnalysis, SectionUnderstanding, ReflectionResult, TranslationIssue, ParagraphStatus
from src.core.format_tokens import TranslationPayload
from src.services.work_checkpoints import WorkCheckpointStore, checkpoint_scope, fingerprint
from src.services.batch_translation_service import BatchTranslationService
from src.services.section_translation_executor import SectionTranslationExecutor
from src.services.translation_resume_service import inspect_translation_resume
from src.services.translation_artifact_service import TranslationArtifactService
from src.llm.work_budget import WorkBudgetExceeded
from src.llm.request_budget import RequestBudgetExceeded


class Provider:
    model_name='test'
    def __init__(self):
        self.draft_calls=[];self.review_calls=[];self.revision_calls=[]
        self.fail_draft_id=None;self.fail_review_at=0;self.issue=False
    def translate_section(self,text,title,context,ids):
        self.draft_calls.append(list(ids))
        if self.fail_draft_id in ids:raise RuntimeError('draft failure')
        return [{'id':key,'translation':f'译文{key}'} for key in ids]
    def reflect_on_translation(self,**kwargs):
        self.review_calls.append(kwargs)
        if len(self.review_calls)==self.fail_review_at: raise RuntimeError('review failure')
        if self.issue and not kwargs['translations'][0].startswith('修订'):
            return {'issues':[{'paragraph_index':0,'issue_type':'accuracy','severity':'high','priority':'P1',
                'original_text':kwargs['source_paragraphs'][0], 'translation_text':kwargs['translations'][0],
                'description':'具体误译','why_it_matters':'原意改变','suggestion':'修正该段'}]}
        return {'issues':[]}
    def refine_and_polish_batch(self,pairs,context):
        self.revision_calls.append(pairs)
        return ['修订'+item['translation'] for item in pairs]


def section(n=2):
    return Section(section_id='s1',title='Example',paragraphs=[Paragraph(id=f'p{i}',index=i,source=f'Source {i}') for i in range(n)])


def translator(provider,sec,threshold=8):
    ctx=LayeredContextManager()
    ctx.set_article_analysis(ArticleAnalysis(theme='test',section_roles={'s1':SectionUnderstanding(role_in_article='body')}))
    t=FourStepTranslator(provider,ctx,paragraph_threshold=threshold)
    return t


def test_completed_draft_batch_survives_later_batch_failure(tmp_path):
    p=Provider();s=section();p.fail_draft_id='p1'
    cache=WorkCheckpointStore(tmp_path/'cache')
    with checkpoint_scope(cache):
        with pytest.raises(RuntimeError): translator(p,s,1).translate_section(s,[s])
    p.fail_draft_id=None
    with checkpoint_scope(WorkCheckpointStore(cache.root)):
        result=translator(p,s,1).translate_section(s,[s])
    assert result.assessment.passed
    assert p.draft_calls==[['p0'],['p1'],['p1']]


def test_drafts_are_not_regenerated_when_only_review_is_pending(tmp_path):
    p=Provider();p.fail_review_at=1;s=section();cache=WorkCheckpointStore(tmp_path/'cache')
    with checkpoint_scope(cache):result=translator(p,s).translate_section(s,[s])
    assert result.degraded and result.translations==['译文p0','译文p1']
    for para,text in zip(s.paragraphs,result.translations):para.add_translation(text,'pro')
    with checkpoint_scope(cache):result=translator(p,s).translate_section(s,[s],resume_drafts=True)
    assert result.assessment.passed and len(p.draft_calls)==1 and len(p.review_calls)==2


def test_revision_and_initial_review_are_reused_after_verification_failure(tmp_path):
    p=Provider();p.issue=True;p.fail_review_at=2;s=section();cache=WorkCheckpointStore(tmp_path/'cache')
    with checkpoint_scope(cache):r1=translator(p,s).translate_section(s,[s])
    assert r1.degraded and r1.revised_translations[0].startswith('修订')
    with checkpoint_scope(cache):r2=translator(p,s).translate_section(s,[s])
    assert not r2.degraded and r2.assessment.passed
    assert len(p.draft_calls)==1 and len(p.revision_calls)==1
    assert len(p.review_calls)==3 # old successful review reused; only failed verification repeated


def test_pending_review_gets_whole_selected_source_not_only_bad_sentences():
    p=Provider();s=section(4)
    for para in s.paragraphs:para.add_translation('旧稿'+para.id,'pro')
    result=translator(p,s).translate_section(s,[s],resume_drafts=True)
    assert result.assessment.passed and not p.draft_calls
    assert p.review_calls[0]['source_paragraphs']==[v.source for v in s.paragraphs]


def test_budget_exhaustion_returns_pending_draft_and_pause():
    p=Provider();s=section()
    def no_budget(**kw):raise WorkBudgetExceeded('done')
    p.reflect_on_translation=no_budget
    result=translator(p,s).translate_section(s,[s])
    assert result.paused and result.degraded and result.assessment is None
    assert result.translations==['译文p0','译文p1']


def test_invalid_review_cannot_be_checkpointed_as_passed(tmp_path):
    p=Provider();s=section();p.reflect_on_translation=lambda **kw:{'issues':[{'paragraph_index':99}]}
    cache=WorkCheckpointStore(tmp_path/'cache')
    with checkpoint_scope(cache):r=translator(p,s).translate_section(s,[s])
    assert r.degraded and not list(cache.root.glob('review-*.json'))


def test_compact_review_has_no_fabricated_score_or_learning():
    p=Provider();s=section();t=translator(p,s);t.compact_review=True;t.memory_service=None
    r=t.translate_section(s,[s])
    assert r.assessment.passed and r.reflection.scores_available is False
    assert not r.assessment.scores_available and r.assessment.scores=={}
    assert p.review_calls[0]['context']['compact_review'] is True
    memory=Mock();t.memory_service=memory;t.commit_section_feedback(r)
    memory._spawn_background.assert_not_called()


def test_partial_draft_does_not_regenerate_completed_ids(tmp_path):
    class Partial(Provider):
        def translate_section(self,text,title,context,ids):return [{'id':'p0','translation':'已成功'}]
    p=Partial();s=section();t=translator(p,s);fallback=[]
    def single(para,*a,**k):fallback.append(para.id);return TranslationPayload(text='补译')
    t._translate_single_paragraph=single
    with checkpoint_scope(WorkCheckpointStore(tmp_path/'cache')):
        result=t._translate_batch(s,s.paragraphs,SectionUnderstanding(),[s])
    assert [v.text for v in result]==['已成功','补译'] and fallback==['p1']


def test_rendered_draft_budget_splits_without_losing_ids():
    p=Provider();p._request_budget_config={'input_token_limit':15,'max_tokens':5}
    p.local_token_counter=len
    p._build_batch_translation_prompt=lambda text,title,ctx,ids:'context'+('x'*5*len(ids))
    s=section(4);t=translator(p,s)
    result=t._translate_batch(s,s.paragraphs,SectionUnderstanding(),[s])
    assert len(result)==4 and p.draft_calls==[['p0'],['p1'],['p2'],['p3']]
    p._request_budget_config['input_token_limit']=5
    with pytest.raises(RequestBudgetExceeded):t._translate_batch(s,[s.paragraphs[0]],SectionUnderstanding(),[s])
    assert len(p.draft_calls)==4 # no request sent for impossible single paragraph


def test_rendered_revision_split_keeps_noncontiguous_paragraph_mapping():
    p=Provider();p._request_budget_config={'input_token_limit':12,'max_tokens':5}
    p.local_token_counter=len;p._build_refine_and_polish_prompt=lambda pairs,scores,ctx:'rules'+('x'*5*len(pairs))
    s=section(6);t=translator(p,s)
    issues=[TranslationIssue(paragraph_index=i,issue_type='accuracy',description='fix',suggestion='fix') for i in [1,3,5]]
    old=[TranslationPayload(text='原稿'+str(i)) for i in range(6)]
    result=t._step_refine_and_polish(s,old,ReflectionResult(issues=issues),SectionUnderstanding(),issues_filter=issues,polish_all=False)
    assert [v.text for v in result]==['原稿0','修订原稿1','原稿2','修订原稿3','原稿4','修订原稿5']
    assert [[v['paragraph_id'] for v in batch] for batch in p.revision_calls]==[['p1'],['p3'],['p5']]


def proof_service():
    service=BatchTranslationService.__new__(BatchTranslationService)
    service.translation_mode='four_step';service._quality_policy='policy1'
    return service


def test_quality_proof_binds_source_text_and_policy_and_protects_human_edits():
    svc=proof_service();p=section().paragraphs[0];p.add_translation('draft','pro')
    assert svc._needs_quality_review(p)
    record=p.latest_translation(non_empty=True)
    record.quality_review={'status':'complete','source':fingerprint(p.source),'text':fingerprint(record.text),'policy':'policy1'}
    assert not svc._needs_quality_review(p)
    p.source+='change';assert svc._needs_quality_review(p)
    p.status=ParagraphStatus.MODIFIED;assert not svc._needs_quality_review(p)
    p.status=ParagraphStatus.TRANSLATED;p.confirm('manual');assert not svc._needs_quality_review(p)


def test_review_pending_drafts_are_included_but_confirmed_text_is_untouched():
    s=section(3)
    s.paragraphs[0].add_translation('draft','pro');s.paragraphs[1].confirm('human')
    selection=SectionTranslationExecutor._build_translatable_section(s,needs_quality_review=proof_service()._needs_quality_review)
    assert [p.id for p in selection.paragraphs]==['p0','p2']
    selection.paragraphs[0].source='changed'
    assert s.paragraphs[0].source=='Source 0'


@pytest.mark.parametrize('have_drafts',[True,False])
def test_resume_inspector_supports_quality_only_or_analysis_only(tmp_path,have_drafts):
    s=section()
    if have_drafts:
        for p in s.paragraphs:p.add_translation('draft','pro')
    pm=SimpleNamespace(projects_path=tmp_path,get_sections=lambda _: [s])
    artifacts=TranslationArtifactService(tmp_path);run_id,folder=artifacts.create_run_artifact_dir('project')
    artifacts.write_json(folder/'run-summary.json',{'status':'incomplete','run_id':run_id,'translation_mode':'four_step'})
    if not have_drafts:
        cache=WorkCheckpointStore(tmp_path/'project'/'artifacts'/'work-checkpoints-v1')
        cache.save('analysis',fingerprint('source'),{'theme':'x'})
    assert inspect_translation_resume(pm,'project').resumable


def test_analysis_fingerprint_excludes_current_translation_but_not_source():
    s=section();p=SimpleNamespace(title='Title',sections=[s]);svc=proof_service()
    old=fingerprint(svc._analysis_inputs(p));s.paragraphs[0].add_translation('draft','pro')
    assert fingerprint(svc._analysis_inputs(p))==old
    s.paragraphs[0].source+=' edit'
    assert fingerprint(svc._analysis_inputs(p))!=old
