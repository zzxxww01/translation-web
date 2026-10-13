"""No real provider requests: stage reuse and admission are observable contracts."""
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from types import SimpleNamespace
from threading import Event
import json
import time

import pytest
from pydantic import ValidationError
from src.config.efficiency import EfficiencyOptions
from src.services.work_checkpoints import (
    WorkCheckpointStore, checkpoint_scope, fresh_stage_scope, checkpoint_call,
    fingerprint, provider_fingerprint,
)
from src.llm.work_budget import WorkBudgetExceeded, work_budget_scope, admit_transport, retry_action
from src.llm.execution_context import check_active, cancellation_scope, generation_budget
from src.llm.request_budget import RequestLimits, RequestBudgetExceeded, check_request, count_request
from src.llm.rate_limiter import transport_slot
from src.llm.phase_provider import phase_provider
from src.llm.errors import LLMConfigurationError, LLMRequestCancelledError, LLMOutputTruncatedError, LLMTimeoutError
from src.prompts.contracts import PromptContractError


@pytest.fixture
def store(tmp_path):
    return WorkCheckpointStore(tmp_path / 'project-a' / 'cache')


def test_valid_result_is_reused_across_instances_and_returns_a_copy(store):
    key = fingerprint({'text': 'source'})
    store.save('draft', key, {'items': ['one']})
    second = WorkCheckpointStore(store.root)
    result = second.load('draft', key, dict)
    result['items'].append('changed')
    assert second.load('draft', key, dict) == {'items': ['one']}
    assert WorkCheckpointStore(store.root.parent.parent/'b'/'cache').load('draft', key, dict) is None


@pytest.mark.parametrize('change', ['digest', 'schema', 'key', 'task', 'broken', 'oversized'])
def test_corrupt_or_incompatible_checkpoint_is_miss(store, change):
    key = fingerprint('source')
    store.save('draft', key, {'answer':'fine'})
    path = store._path('draft', key)
    data = json.loads(path.read_text())
    if change == 'broken':
        path.write_text('{')
    elif change == 'oversized':
        store.MAX_BYTES=10
    else:
        data[{'digest': 'result_digest'}.get(change, change)] = 'changed'
        path.write_text(json.dumps(data))
    assert store.load('draft', key, dict) is None


@pytest.mark.parametrize('task,key', [('../x','a'*64), ('a','../x'), ('a','a'*63), ('A','a'*64)])
def test_checkpoint_paths_are_validated_before_writing(store, task, key):
    with pytest.raises(ValueError):
        store.save(task,key,{'x':1})


def test_checkpoint_rejects_symlinks(store,tmp_path):
    target=tmp_path/'external';target.mkdir()
    link=tmp_path/'link';link.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError): WorkCheckpointStore(link)
    key=fingerprint(1)
    external=target/'file';external.write_text('untouched')
    (store.root/f'draft-{key}.json').symlink_to(external)
    with pytest.raises(ValueError): store.save('draft',key,{'new':1})
    assert external.read_text()=='untouched'


def test_count_and_size_bounds_do_not_evict_canonical_work(store):
    store.MAX_ENTRIES=2
    for i in range(5): store.save('draft',fingerprint(i),{'i':i})
    assert len(list(store.root.glob('*.json')))==2
    store.MAX_BYTES=20
    store.save('draft',fingerprint('large'),{'x':'x'*100})
    assert not store._path('draft',fingerprint('large')).exists()


def test_atomic_checkpoint_write_failure_preserves_previous(store,monkeypatch):
    key=fingerprint(1);store.save('draft',key,{'ok':1})
    path=store._path('draft',key);before=path.read_bytes()
    def fail(*a,**k): raise OSError('disk')
    monkeypatch.setattr('src.services.work_checkpoints.write_json_atomic',fail)
    with pytest.raises(OSError): store.save('draft',key,{'ok':2})
    assert path.read_bytes()==before


def test_cache_revalidates_and_explicit_retranslation_bypasses(store):
    calls=[]; provider=SimpleNamespace(model_name='test')
    def invoke(): calls.append(1);return {'value':len(calls)}
    with checkpoint_scope(store):
        assert checkpoint_call('test',provider,{'s':1},invoke,dict)=={'value':1}
        assert checkpoint_call('test',provider,{'s':1},invoke,dict)=={'value':1}
        with fresh_stage_scope(True):
            assert checkpoint_call('test',provider,{'s':1},invoke,dict)=={'value':2}
        assert checkpoint_call('test',provider,{'s':1},invoke,dict)=={'value':2}
        assert checkpoint_call('test',provider,{'s':2},invoke,dict)=={'value':3}
    assert len(calls)==3


def test_new_model_or_rules_invalidates_cache(store,monkeypatch):
    calls=[];p=SimpleNamespace(model_name='one')
    def run(): calls.append(1);return {'ok':1}
    monkeypatch.setattr('src.services.work_checkpoints.prompt_fingerprint',lambda *a:'v1')
    with checkpoint_scope(store):
        checkpoint_call('test',p,{},run,dict)
        p.model_name='two';checkpoint_call('test',p,{},run,dict)
        monkeypatch.setattr('src.services.work_checkpoints.prompt_fingerprint',lambda *a:'v2')
        checkpoint_call('test',p,{},run,dict)
    assert len(calls)==3


def test_failed_or_incomplete_stage_does_not_poison_cache(store):
    p=SimpleNamespace(model_name='one')
    with checkpoint_scope(store):
        with pytest.raises(RuntimeError):
            checkpoint_call('test',p,{},lambda:(_ for _ in ()).throw(RuntimeError('failure')),dict)
        assert checkpoint_call('test',p,{},lambda:{'partial':True},dict,cacheable=lambda _:False)=={'partial':True}
    assert not list(store.root.glob('*.json'))


def test_cancelled_worker_does_not_write_late_checkpoint(store):
    event=Event()
    def finish(): event.set();return {'ok':1}
    with checkpoint_scope(store),cancellation_scope(event):
        with pytest.raises(LLMRequestCancelledError):
            checkpoint_call('test',object(),{},finish,dict)
    assert not list(store.root.glob('*.json'))


def test_partial_response_kept_but_not_saved_as_complete(store):
    with checkpoint_scope(store):
        result=checkpoint_call('draft',object(),{},lambda:['done'],list,cacheable=lambda v:len(v)==2)
    assert result==['done'] and store.writes==0


def test_shared_admission_is_atomic_across_threads_and_nested_scopes():
    def work():
        with transport_slot(): return 1
    with work_budget_scope('run',30,3) as run:
        with work_budget_scope('stage',30,2) as stage:
            with ThreadPoolExecutor(8) as pool:
                futures=[pool.submit(copy_context().run,work) for _ in range(8)]
            success=sum(f.exception() is None for f in futures)
            assert success==2 and run.calls==stage.calls==2
        with transport_slot(): check_active()
        assert run.calls==3
        with pytest.raises(WorkBudgetExceeded):
            with transport_slot(): pass


def test_last_admitted_response_and_checkpoint_are_kept(store):
    with work_budget_scope('stage',30,1),checkpoint_scope(store):
        def call():
            with transport_slot(): return {'answer':'last'}
        assert checkpoint_call('test',object(),{},call,dict)=={'answer':'last'}
        assert checkpoint_call('test',object(),{},call,dict)=={'answer':'last'}
        with pytest.raises(WorkBudgetExceeded): admit_transport()
    assert store.writes==1


def test_nested_generation_decorators_do_not_double_count():
    class Provider:
        timeout=30
        @generation_budget
        def generate(self,prompt,**kwargs):
            with transport_slot(): return 'ok'
    class Wrapper:
        timeout=30
        @generation_budget
        def generate(self,prompt,**kwargs): return Provider().generate(prompt)
    with work_budget_scope('stage',30,1) as budget:
        assert Wrapper().generate('x')=='ok'
        assert budget.calls==1


def test_parent_deadline_and_cancel_are_shared_not_reset(monkeypatch):
    clock=[10.0];monkeypatch.setattr('time.monotonic',lambda:clock[0])
    with work_budget_scope('run',5,20):
        clock[0]=14
        with work_budget_scope('stage',100,20):
            clock[0]=16
            with pytest.raises(WorkBudgetExceeded):check_active()
    with work_budget_scope('run',5,20,should_cancel=lambda:True):
        with pytest.raises(LLMRequestCancelledError):admit_transport()


@pytest.mark.parametrize('error,action',[
    (LLMConfigurationError('key'),'stop'),(WorkBudgetExceeded('full'),'stop'),
    (LLMRequestCancelledError('stop'),'stop'),(LLMTimeoutError('timeout'),'retry'),
    (RequestBudgetExceeded('window'),'resize'),(LLMOutputTruncatedError('length'),'resize'),
    (PromptContractError('json'),'format'),(ValueError('other'),'stop')])
def test_recovery_uses_error_type(error,action): assert retry_action(error)==action


@pytest.mark.parametrize('options',[{'max_stage_calls':0},{'prescan_concurrency':9},{'resume_stages':'yes'},
    {'unknown':1},{'stage_timeout_seconds':True},{'run_timeout_seconds':0}])
def test_efficiency_policy_is_strict(options):
    with pytest.raises(ValidationError):EfficiencyOptions(**options)


def test_full_request_includes_context_and_output_reservation():
    assert check_request('text',RequestLimits(input_tokens=200,context_tokens=220,reserve_output_tokens=20))['input_tokens']>0
    with pytest.raises(RequestBudgetExceeded):check_request('规则'*100,RequestLimits(input_tokens=200))
    with pytest.raises(RequestBudgetExceeded):check_request('text',RequestLimits(context_tokens=150,reserve_output_tokens=100))
    with pytest.raises(RequestBudgetExceeded):check_request('text',RequestLimits(output_tokens=20,reserve_output_tokens=100))


def test_optional_local_counter_is_cached_by_model_and_exact_input():
    calls=[]
    def counter(prompt):calls.append(prompt);return len(prompt)
    assert count_request('one',model='m1',counter=counter)==(3,'exact_local_counter')
    count_request('one',model='m1',counter=counter)
    count_request('one',model='m2',counter=counter)
    count_request('two',model='m1',counter=counter)
    assert calls==['one','one','two']


@pytest.mark.parametrize('count',[-1,True,1.5])
def test_invalid_local_counter_is_rejected(count):
    with pytest.raises(ValueError): count_request('x',counter=lambda _:count)


def test_phase_facades_do_not_mutate_shared_client_and_zero_is_real():
    class Provider:
        model_name='m1'
        def __init__(self):self.calls=[]
        def generate(self,prompt,**kwargs):self.calls.append(kwargs);return 'ok'
    raw=Provider()
    draft=phase_provider(raw,{'temperature':0,'max_tokens':123})
    review=phase_provider(raw,{'temperature':0.7,'max_tokens':456})
    draft.generate('x',temperature=0.9)
    review.generate('x',temperature=0.9)
    assert [v['temperature'] for v in raw.calls]==[0,0.7]
    assert [v['max_tokens'] for v in raw.calls]==[123,456]
    assert not hasattr(raw,'_phase_config')
    assert provider_fingerprint(draft)!=provider_fingerprint(review)


@pytest.mark.parametrize('config',[{'temperature':True},{'temperature':float('nan')},{'max_tokens':0},{'timeout':-1}])
def test_bad_phase_settings_fail_before_request(config):
    with pytest.raises(ValueError):phase_provider(object(),config)
