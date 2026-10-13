"""Regression coverage for conflicts between main and the two efficiency PRs."""
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from types import SimpleNamespace
import json
import time

import pytest

from src.api.routers.translate_models import LongformWorkflowStartRequest
from src.api.utils.json_utils import parse_llm_json_response, normalize_control_keys
from src.config.efficiency import EfficiencyOptions
from src.core.models import Paragraph, ParagraphStatus, Section
from src.llm.execution_context import generation_budget
from src.llm.rate_limiter import transport_slot
from src.llm.request_budget import check_provider_request, RequestBudgetExceeded
from src.llm.work_budget import work_budget_scope, WorkBudgetExceeded
from src.prompts.contracts import PromptContractError
from src.services.stage_checkpoints import StageCheckpoints, checkpoint_scope as legacy_scope
from src.services.work_checkpoints import WorkCheckpointStore, checkpoint_scope, checkpoint_call, fingerprint
from src.services.batch_translation_service import BatchTranslationService


@pytest.mark.parametrize('payload', [
    {'efficiency': {'stage_resume': True, 'resume_stages': False}},
    {'efficiency': {'max_stage_seconds': 120, 'stage_timeout_seconds': 180}},
    {'model_scope': 'all', 'efficiency': {'model_scope': 'draft'}},
    {'model_profile': 'default', 'efficiency': {'profile': 'premium'}},
])
def test_conflicting_legacy_and_current_options_are_not_silently_dropped(payload):
    with pytest.raises(ValueError):
        LongformWorkflowStartRequest.model_validate(payload)


def test_nested_scope_reaches_public_route_and_aliases_share_canonical_policy():
    from src.core.efficiency import EfficiencyOptions as OldOptions
    assert OldOptions is EfficiencyOptions
    value = LongformWorkflowStartRequest.model_validate({'efficiency': {
        'model_scope': 'draft', 'profile': 'premium', 'stage_resume': False,
        'max_stage_seconds': 120, 'max_run_seconds': 900}})
    assert value.model_scope == 'draft' and value.model_profile == 'premium'
    assert value.efficiency.resume_stages is False
    assert value.efficiency.stage_timeout_seconds == 120
    assert value.efficiency.run_timeout_seconds == 900
    assert EfficiencyOptions().prescan_concurrency == 1


def test_logical_and_real_transport_budgets_use_explicit_units():
    from src.llm.business_budget import run_budget
    class Provider:
        timeout = 10
        @generation_budget
        def generate(self, prompt, **kwargs):
            with transport_slot():
                return 'ok'
    with run_budget(EfficiencyOptions(max_run_calls=2)) as logical:
        with work_budget_scope('real-transports', 10, 1) as actual:
            assert Provider().generate('first') == 'ok'
            assert logical.calls == actual.calls == 1
            with pytest.raises(WorkBudgetExceeded):
                Provider().generate('second')
            assert actual.calls == 1  # a rejected local attempt never reaches HTTP


def test_estimated_run_tokens_are_reserved_on_transport_not_on_cache_hit():
    class Provider:
        timeout = 10
        @generation_budget
        def generate(self, prompt, **kwargs):
            with transport_slot():
                return 'ok'
    with work_budget_scope('article', 10, 10, max_tokens=1) as budget:
        with pytest.raises(WorkBudgetExceeded):
            Provider().generate('text')
        assert budget.calls == budget.estimated_tokens == 0


def test_explicit_output_limit_is_checked_not_an_unrelated_default():
    provider = SimpleNamespace(_request_budget_config={'context_window_tokens': 1000, 'max_tokens': 8192})
    assert check_provider_request(provider, 'text', output_limit=100)['reserved_output_tokens'] == 100
    with pytest.raises(RequestBudgetExceeded):
        check_provider_request(provider, 'text', output_limit=1000)


def test_same_canonical_checkpoint_is_singleflight_across_instances(tmp_path):
    calls = []
    guard = Lock()
    def fetch():
        with guard:
            calls.append(1)
        time.sleep(0.03)
        return {'ok': True}
    def run():
        with checkpoint_scope(WorkCheckpointStore(tmp_path / 'work')):
            return checkpoint_call('draft', object(), {'source': 'one'}, fetch, dict)
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert list(pool.map(lambda _: run(), range(4))) == [{'ok': True}] * 4
    assert len(calls) == 1


def test_legacy_namespace_also_invalidates_canonical_pipeline_calls(tmp_path):
    def run(namespace, answer):
        with legacy_scope(StageCheckpoints(tmp_path, namespace)):
            return checkpoint_call('draft', object(), {}, lambda: {'answer': answer}, dict)
    assert run('old', 'first') == {'answer': 'first'}
    assert run('new', 'second') == {'answer': 'second'}
    assert run('old', 'wrong') == {'answer': 'first'}


def test_custom_legacy_encoder_is_identical_on_fresh_and_cached_results(tmp_path):
    store = StageCheckpoints(tmp_path, 'custom')
    calls = []
    def call():
        calls.append(1)
        return ('text', 3)
    def encode(value):
        return {'name': value[0], 'index': value[1]}
    def decode(value):
        return value['name'], value['index']
    for _ in range(2):
        assert store.compute('draft', {}, call, encode=encode, decode=decode) == ('text', 3)
    assert len(calls) == 1


@pytest.mark.parametrize('response', [
    '{"versions":[],"versions":[]}', '{"score":NaN}',
    '{"score":Infinity}', '{"versions":[]} }', '{"versions":[]} {"extra":1}',
])
def test_relay_recovery_does_not_relax_structure_or_duplicate_checks(response):
    with pytest.raises(PromptContractError):
        parse_llm_json_response(response)


def test_control_character_recovery_preserves_collision_rejection():
    data = parse_llm_json_response('{"english\n":"Hello\nworld"}')
    assert normalize_control_keys(data, ['english']) == {'english': 'Hello\nworld'}
    with pytest.raises(PromptContractError):
        normalize_control_keys({'english': 'one', 'english\n': 'two'}, ['english'])


def test_quality_proof_requires_current_text_and_export_safe_markup():
    paragraph = Paragraph(id='p', index=0, source='source')
    paragraph.add_translation('text', 'm')
    record = paragraph.translations['m']
    record.quality_review = {'status': 'complete', 'source': fingerprint('source'),
                             'text': fingerprint('text'), 'policy': 'v1'}
    assert not paragraph.needs_quality_review('v1')
    record.format_issues = ['invalid code token']
    assert paragraph.needs_quality_review('v1')
    record.format_issues = []
    record.text = 'edited'
    assert paragraph.needs_quality_review('v1')
    paragraph.status = ParagraphStatus.MODIFIED
    assert not paragraph.needs_quality_review('v1')  # explicit human work remains protected


@pytest.mark.asyncio
async def test_ordinary_section_path_splits_complete_requests_and_reuses_valid_batches(tmp_path):
    class Provider:
        model_name = 'fake'
        _request_budget_config = {'input_token_limit': 500, 'max_tokens': 100}
        def __init__(self):
            self.calls = []
        def _build_batch_translation_prompt(self, text, title, context, ids):
            return 'rules' * 20 + text
        def translate_section(self, **kwargs):
            self.calls.append(kwargs['paragraph_ids'])
            return [{'id': key, 'translation': 'translated ' + key} for key in kwargs['paragraph_ids']]
    p = Provider()
    section = Section(section_id='s', title='Example', paragraphs=[Paragraph(id=f'p{i}', index=i, source='a'*150) for i in range(3)])
    service = BatchTranslationService.__new__(BatchTranslationService)
    service._retranslate_scope = 'resume'
    async def translate():
        return await service._call_section_batch(provider=p, section=section, context={}, format_tokens=[],
            batch_lines=[f'[{item.id}] {item.source}' for item in section.paragraphs],
            batch_ids=[item.id for item in section.paragraphs])
    with checkpoint_scope(WorkCheckpointStore(tmp_path / 'cache')):
        assert [item['id'] for item in await translate()] == ['p0', 'p1', 'p2']
        first = list(p.calls)
        assert len(first) == 3 and all(len(ids) == 1 for ids in first)
        await translate()
        assert p.calls == first
