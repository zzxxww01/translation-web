"""No paid calls. Regressions for budgets, quotas, cache usage and aggregation."""
import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextvars import ContextVar
from types import SimpleNamespace as NS
from unittest.mock import Mock

import pytest

from src.llm import execution_context as ec
from src.llm.config_models import RateLimitConfig
from src.llm.errors import LLMDeadlineExceededError, LLMRequestCancelledError, LLMUpstreamUnavailableError, LLMOutputTruncatedError
from src.llm.provider_adapter import ProviderAdapter
from src.llm.rate_limiter import ProviderLimiter, transport_slot
from src.llm.token_usage import gemini_usage, openai_usage
from src.llm.usage_metrics import LLMUsageMetrics
from src.llm.costing import estimate_token_cost


def adapter(outcomes, runtime=None):
    transport = Mock()
    transport.generate.side_effect = outcomes
    obj = ProviderAdapter.__new__(ProviderAdapter)
    obj.model_alias = 'test'
    obj.attempt_plan = [NS(provider=NS(provider_id='test-relay', type='vectorengine'),
        model=NS(alias='test', real_model='test-real', config=runtime or {}), api_key=NS(name='test', key='not-a-key'))]
    obj.create_provider = Mock(return_value=transport)
    return obj, transport


def test_fallback_receives_remaining_budget_instead_of_reset(monkeypatch):
    now = [100.0]
    monkeypatch.setattr(ec.time, 'monotonic', lambda: now[0])
    monkeypatch.setattr(ec.time, 'sleep', lambda duration: now.__setitem__(0, now[0] + duration))
    timeouts = []
    def generate(**kwargs):
        timeouts.append(kwargs['timeout'])
        if len(timeouts) == 1:
            now[0] += 4.0
            raise LLMUpstreamUnavailableError('503')
        return 'ok'
    obj, _ = adapter(generate)
    assert obj.generate_with_fallback('p', timeout=5) == 'ok'
    assert timeouts == [5.0, 0.5]
    assert ec.remaining_timeout() is None


def test_exhausted_budget_does_not_send_fallback(monkeypatch):
    now = [100.0]
    monkeypatch.setattr(ec.time, 'monotonic', lambda: now[0])
    def fail(**kwargs):
        now[0] += 4.9
        raise LLMUpstreamUnavailableError('503')
    obj, transport = adapter(fail)
    with pytest.raises(LLMDeadlineExceededError):
        obj.generate_with_fallback('p', timeout=5)
    assert transport.generate.call_count == 1


@pytest.mark.parametrize('timeout', [0, -1, True, float('nan'), float('inf')])
def test_invalid_budget_never_reaches_transport(timeout):
    obj, transport = adapter(['ok'])
    with pytest.raises(ValueError):
        obj.generate_with_fallback('p', timeout=timeout)
    transport.generate.assert_not_called()


def test_abandonment_prevents_additional_requests():
    cancelled = threading.Event()
    def fail(**kwargs):
        cancelled.set()
        raise LLMUpstreamUnavailableError('503')
    obj, transport = adapter(fail)
    with ec.cancellation_scope(cancelled), pytest.raises(LLMRequestCancelledError):
        obj.generate_with_fallback('p')
    assert transport.generate.call_count == 1


def test_route_runtime_values_and_explicit_overrides():
    obj, transport = adapter(['ok', 'ok'], {'max_tokens': 123, 'temperature': 0.0, 'timeout': 40})
    obj.generate_with_fallback('p')
    assert transport.generate.call_args.kwargs['max_tokens'] == 123
    assert transport.generate.call_args.kwargs['temperature'] == 0.0
    obj.generate_with_fallback('p', max_tokens=456, temperature=0.3)
    assert transport.generate.call_args.kwargs['max_tokens'] == 456
    assert transport.generate.call_args.kwargs['temperature'] == 0.3


def test_duplicate_model_aliases_do_not_repeat_the_same_route():
    obj, _ = adapter(['ok'])
    original = obj.attempt_plan[0]
    duplicate = NS(provider=original.provider, api_key=original.api_key,
                   model=NS(alias='another-alias', real_model='test-real', config={}))
    third = NS(provider=original.provider, api_key=original.api_key,
               model=NS(alias='third', real_model='other-real', config={}))
    obj.attempt_plan = [original, duplicate, third]
    assert [item.model.real_model for item in obj._bounded_attempt_plan()] == ['test-real', 'other-real']


@pytest.mark.parametrize('key,value', [('max_concurrent',0), ('max_concurrent',True), ('requests_per_minute',-1), ('requests_per_minute',1.5)])
def test_invalid_rate_limit_is_rejected(key,value):
    data = dict(max_concurrent=2, requests_per_minute=60)
    data[key] = value
    with pytest.raises(ValueError):
        RateLimitConfig(**data)


def test_provider_quota_is_shared_and_holds_real_transport_lifetime():
    counts = [0,0]
    lock = threading.Lock()
    def invoke():
        with ec.route_scope('regression-shared-quota', RateLimitConfig(2,60)), transport_slot():
            with lock:
                counts[0] += 1
                counts[1] = max(counts)
            time.sleep(0.02)
            with lock:
                counts[0] -= 1
    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(lambda _: invoke(), range(12)))
    assert counts == [0,2]


def test_rpm_counts_request_starts_even_after_failure():
    limiter = ProviderLimiter(2,1)
    with pytest.raises(ValueError), limiter.acquire():
        raise ValueError('response failed')
    class Caller:
        @ec.generation_budget
        def call(self, timeout):
            with limiter.acquire():
                pytest.fail('Quota was incorrectly released by a failed response')
    with pytest.raises(LLMDeadlineExceededError):
        Caller().call(timeout=0.025)
    assert limiter.running == 0
    assert len(limiter.starts) == 1


def test_gemini_timeout_thread_inherits_scoped_context():
    from src.llm.gemini import GeminiProvider
    variable = ContextVar('test_scope', default='missing')
    variable.set('preserved')
    provider = GeminiProvider.__new__(GeminiProvider)
    assert provider._generate_with_timeout_fn(variable.get, 1) == 'preserved'


def test_gemini_output_limit_reaches_sdk_and_usage_preserves_thinking(monkeypatch):
    from src.llm import gemini as gm
    provider = gm.GeminiProvider.__new__(gm.GeminiProvider)
    provider.model_name, provider.backup_model, provider.api_keys = 'model', None, ['fake']
    provider.max_attempts, provider.request_timeout, provider.retry_delay = 1, 2, .5
    provider.network_policy = NS()
    provider.model_type = 'pro'
    provider._use_rest_transport = lambda: False
    response = NS(text='translated', candidates=[NS(finish_reason='STOP')],
        usage_metadata=NS(prompt_token_count=100,candidates_token_count=20,thoughts_token_count=30,
                          total_token_count=150,cached_content_token_count=70))
    client = NS(models=NS(generate_content=Mock(return_value=response)))
    provider._get_client = lambda _: client
    metrics = LLMUsageMetrics()
    monkeypatch.setattr(gm, 'llm_usage_metrics', metrics)
    assert provider.generate('source', max_tokens=321) == 'translated'
    config = client.models.generate_content.call_args.kwargs['config']
    assert config['max_output_tokens'] == 321
    assert config['http_options']['retry_options']['attempts'] == 1
    assert metrics.summary()['billable_output_tokens'] == 50
    assert metrics.summary()['cached_input_tokens'] == 70
    assert ec.output_limit() is None
    # Truncated output has usage too, even though it must never be accepted.
    response.candidates[0].finish_reason = 'MAX_TOKENS'
    with pytest.raises(LLMOutputTruncatedError):
        provider.generate('source', max_tokens=42)
    assert metrics.summary()['failed_billable_output_tokens'] == 50


def test_gemini_records_each_failed_attempt_not_only_final_success(monkeypatch):
    from src.llm import gemini as gm
    provider = gm.GeminiProvider.__new__(gm.GeminiProvider)
    provider.model_name, provider.backup_model, provider.api_keys = 'model', None, ['fake']
    provider.max_attempts, provider.request_timeout, provider.retry_delay = 2, 3, .5
    provider._generate_once = Mock(side_effect=[LLMUpstreamUnavailableError('503'), gm.GeminiGenerationResult(text='ok')])
    monkeypatch.setattr(ec.time, 'sleep', lambda _: None)
    metrics = LLMUsageMetrics()
    monkeypatch.setattr(gm, 'llm_usage_metrics', metrics)
    assert provider.generate('p') == 'ok'
    summary = metrics.summary()
    assert summary['api_calls'] == 2
    assert summary['successful_calls'] == summary['failed_calls'] == 1
    assert summary['unknown_input_calls'] == 2


@pytest.mark.parametrize('raw,expected', [
    ({'prompt_tokens':100,'completion_tokens':50,'prompt_tokens_details':{'cached_tokens':80},'completion_tokens_details':{'reasoning_tokens':30}},(100,50,80,30)),
    ({'prompt_tokens':100,'completion_tokens':50,'prompt_cache_hit_tokens':60},(100,50,60,None)),
    ({'prompt_tokens':10,'completion_tokens':False,'prompt_cache_hit_tokens':15},(10,None,None,None)),
])
def test_openai_usage_does_not_double_count_reasoning(raw,expected):
    usage = openai_usage(raw)
    assert (usage.input_tokens,usage.billable_output_tokens,usage.cached_input_tokens,usage.reasoning_tokens) == expected


def test_gemini_missing_thoughts_is_not_invented_zero():
    assert gemini_usage({'promptTokenCount':10,'candidatesTokenCount':20}).billable_output_tokens is None
    assert gemini_usage({'promptTokenCount':10,'candidatesTokenCount':20,'totalTokenCount':30}).billable_output_tokens == 20


def test_aggregate_continues_when_call_log_is_full():
    metrics = LLMUsageMetrics()
    metrics._MAX_CALLS_PER_RUN = 2
    for i in range(9):
        metrics.record_call(provider='p',model='m',phase='draft',success=i%2==0,
                            duration_seconds=2, input_tokens=10, output_tokens=5,
                            billable_output_tokens=5,total_tokens=15,cached_input_tokens=4)
    summary = metrics.summary()
    assert summary['api_calls'] == 9
    assert summary['input_tokens'] == 90
    assert summary['total_tokens'] == 135
    assert summary['dropped_call_records'] == 7
    assert len(summary['calls']) == 2
    assert summary['service_seconds'] == 18
    assert summary['groups'][0]['cached_input_tokens'] == 36
    assert 'calls' not in metrics.summary(include_calls=False)


def test_costing_does_not_mix_currencies_or_guess_relay_prices():
    metrics = LLMUsageMetrics()
    metrics.record_call(provider='relay', provider_id='my-relay', model='model', duration_seconds=1,
                        success=True,input_tokens=1000000,billable_output_tokens=100000,cached_input_tokens=600000)
    summary = metrics.summary()
    assert estimate_token_cost(summary, {'rates':[]})['by_currency'] == {}
    row = dict(provider_id='my-relay',model='model',currency='TEST',input_per_million='2',
               cached_input_per_million='0.2',output_per_million='4',source='synthetic test only',effective_date='2026-01-01')
    report = estimate_token_cost(summary, {'rates':[row]})
    assert report['by_currency']['TEST']['known_subtotal_min'] == '1.32'
    assert report['observed_token_pricing_complete']
    assert not report['invoice_complete']
    row['provider_id'] = 'official'
    assert estimate_token_cost(summary, {'rates':[row]})['groups'][0]['status'] == 'missing_price'


def test_character_batched_paragraph_ids_remain_ordered():
    from src.agents.four_step_translator import FourStepTranslator
    obj = FourStepTranslator(Mock(),Mock(),paragraph_threshold=8,batch_source_char_limit=10)
    paragraphs = [NS(id=str(i),source='x'*size) for i,size in enumerate([6,6,5,16,2])]
    batches = obj._split_into_batches(paragraphs)
    assert [[p.id for p in b] for b in batches] == [['0'],['1'],['2'],['3'],['4']]
    assert [p for batch in batches for p in batch] == paragraphs


def test_fixed_prompt_prefix_precedes_dynamic_context():
    from src.llm.vectorengine import VectorEngineProvider
    obj = VectorEngineProvider.__new__(VectorEngineProvider)
    from src.prompts import get_prompt_manager
    obj.prompt_manager = get_prompt_manager()
    context = {'article_theme':'DYNAMIC-UNIQUE-TITLE'}
    rendered = obj._build_reflection_prompt(['source'],['translation'],[],[],context)
    assert rendered.index('中文成文') < rendered.index('DYNAMIC-UNIQUE-TITLE') < rendered.index('原文：source')
    pair = dict(source='s',translation='t',issues=[{'type':'logic','description':'UNIQUE-ISSUE','suggestion':'fix it'}])
    refined = obj._build_refine_and_polish_prompt([pair],{},context)
    assert refined.count('UNIQUE-ISSUE') == 1
