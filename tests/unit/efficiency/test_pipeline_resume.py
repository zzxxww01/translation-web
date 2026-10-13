from collections import Counter
import pytest
from src.agents.four_step_translator import FourStepTranslator
from src.agents.context_manager import LayeredContextManager
from src.core.models import ArticleAnalysis, SectionUnderstanding, Paragraph, Section
from src.services.stage_checkpoints import StageCheckpoints, checkpoint_scope
from src.services.section_translation_executor import SectionTranslationExecutor
from src.prompts.contracts import text_version
from src.llm.business_budget import BusinessBudgetExceeded


class PipelineLLM:
    model_name = 'offline-test-model'
    def __init__(self):
        self.calls = Counter()
        self.fail = None
        self.issue = False
    def translate_section(self, source, title, context, ids):
        self.calls['draft'] += 1
        if self.fail == 'second-batch' and ids == ['p1']:
            self.fail = None
            raise RuntimeError('draft interrupted')
        return [{'id': key, 'translation': f'初稿 {key}'} for key in ids]
    def reflect_on_translation(self, source_paragraphs, translations, **kwargs):
        phase = 'verification' if any(t.startswith('修订') for t in translations) else 'review'
        self.calls[phase] += 1
        if self.fail == phase:
            self.fail = None
            raise RuntimeError(f'{phase} interrupted')
        if self.issue and phase == 'review':
            return {'issues': [{'paragraph_index': 0, 'issue_type': 'accuracy', 'severity': 'high',
                'original_text': source_paragraphs[0], 'translation_text': translations[0],
                'description': 'A verified issue', 'why_it_matters': 'Changes original meaning',
                'suggestion': 'Use the accurate wording'}]}
        return {'issues': []}
    def refine_and_polish_batch(self, pairs, context):
        self.calls['revision'] += 1
        if self.fail == 'revision':
            self.fail = None
            raise RuntimeError('revision interrupted')
        return [f'修订 {pair["paragraph_id"]}' for pair in pairs]


def setup(llm, count=1):
    section = Section(section_id='s1', title='A title', paragraphs=[
        Paragraph(id=f'p{i}', index=i, source=f'Source {i}.') for i in range(count)])
    context = LayeredContextManager()
    context.set_article_analysis(ArticleAnalysis(theme='topic', section_roles={'s1': SectionUnderstanding(role_in_article='body')}))
    translator = FourStepTranslator(llm, context, paragraph_threshold=1)
    return section, translator


def run_new(llm, store, count=1, **kwargs):
    section, translator = setup(llm, count)
    with checkpoint_scope(store):
        result = translator.translate_section(section, [section], **kwargs)
    return result


def test_successful_draft_batch_survives_later_batch_failure(tmp_path):
    llm = PipelineLLM(); llm.fail = 'second-batch'
    store = StageCheckpoints(tmp_path, 'bundle')
    with pytest.raises(RuntimeError): run_new(llm, store, count=2)
    assert llm.calls['draft'] == 2
    result = run_new(llm, store, count=2)
    assert result.assessment.passed
    assert result.translations == ['初稿 p0', '初稿 p1']
    assert llm.calls['draft'] == 3  # only failed batch, not both


@pytest.mark.parametrize('failure', ['review', 'revision', 'verification'])
def test_resume_only_failed_quality_step(tmp_path, failure):
    llm = PipelineLLM(); llm.fail = failure; llm.issue = failure != 'review'
    store = StageCheckpoints(tmp_path, 'bundle')
    first = run_new(llm, store)
    assert first.degraded
    assert first.workflow_status == {'review':'review_pending', 'revision':'revision_pending', 'verification':'verification_pending'}[failure]
    assert first.translations == ['初稿 p0']
    second = run_new(llm, store)
    assert second.assessment.passed and not second.degraded
    assert llm.calls['draft'] == 1
    assert llm.calls[failure] == 2
    if failure != 'review': assert llm.calls['review'] == 1
    if failure == 'verification': assert llm.calls['revision'] == 1


def test_existing_unreviewed_draft_is_reviewed_without_regeneration(tmp_path):
    llm = PipelineLLM()
    section, translator = setup(llm)
    section.paragraphs[0].add_translation('已存初稿', 'm')
    with checkpoint_scope(StageCheckpoints(tmp_path, 'v1')):
        result = translator.translate_section(section, [section], reuse_existing_drafts=True)
    assert result.assessment.passed
    assert result.translations == ['已存初稿']
    assert llm.calls == Counter(review=1)


def test_force_retranslate_does_not_replay_old_answer(tmp_path):
    llm = PipelineLLM(); store = StageCheckpoints(tmp_path, 'bundle')
    assert run_new(llm, store).assessment.passed
    assert run_new(llm, store, reuse_checkpoints=False).assessment.passed
    assert llm.calls == Counter(draft=2, review=2)


def test_changed_source_invalidates_model_outputs(tmp_path):
    llm = PipelineLLM(); store = StageCheckpoints(tmp_path, 'bundle')
    run_new(llm, store)
    section, translator = setup(llm)
    section.paragraphs[0].source = 'A changed source.'
    with checkpoint_scope(store): result = translator.translate_section(section, [section])
    assert result.assessment.passed
    assert llm.calls == Counter(draft=2, review=2)


def test_quality_marker_requires_same_source_text_policy_and_export_format():
    para = Paragraph(id='p', index=0, source='source')
    para.add_translation('初稿', 'm')
    assert para.needs_quality_review('policy')
    record = para.translations['m']
    record.quality_status = 'passed'; record.quality_policy = 'policy'
    record.quality_version = text_version([para.source], [record.text])
    assert not para.needs_quality_review('policy')
    assert para.needs_quality_review('new-policy')
    record.format_issues = ['broken']
    assert para.needs_quality_review('policy')
    record.format_issues = []
    para.source = 'changed'
    assert para.needs_quality_review('policy')
    para.confirm('人工确认')
    assert not para.needs_quality_review('new-policy')


def test_quality_filter_includes_pending_drafts_but_not_confirmed_or_passed():
    section, _ = setup(PipelineLLM(), count=3)
    a, b, c = section.paragraphs
    for p in section.paragraphs: p.add_translation('draft', 'm')
    b.confirm('人工确认')
    c.translations['m'].quality_status = 'passed'
    c.translations['m'].quality_version = text_version([c.source], ['draft'])
    selected = SectionTranslationExecutor._build_translatable_section(section, require_quality=True)
    assert [p.id for p in selected.paragraphs] == ['p0']
    assert not SectionTranslationExecutor._build_translatable_section(section).paragraphs


def test_budget_exhaustion_preserves_draft_and_explicit_pending_status(tmp_path):
    class Limited(PipelineLLM):
        def reflect_on_translation(self, *args, **kwargs):
            raise BusinessBudgetExceeded('stage limit')
    result = run_new(Limited(), StageCheckpoints(tmp_path, 'bundle'))
    assert result.budget_exhausted and result.degraded
    assert result.workflow_status == 'review_pending'
    assert result.assessment is None and result.translations == ['初稿 p0']
