"""Offline regression tests: no config credentials or paid requests."""
from types import SimpleNamespace as NS
from unittest.mock import Mock
import pytest

from src.llm import provider_adapter as pa
from src.llm.errors import LLMUpstreamUnavailableError
from src.llm.base import LLMProvider


def plan(kind='vectorengine', name='relay'):
    return NS(provider=NS(type=kind, provider_id=kind),
              model=NS(alias=name, real_model=name), api_key=NS(name='test', key='fake'))


def adapter(monkeypatch, outcomes, plans=None, alias='relay'):
    obj = pa.ProviderAdapter.__new__(pa.ProviderAdapter)
    obj.model_alias = alias
    obj.attempt_plan = plans or [plan()]
    transport = Mock()
    transport.generate.side_effect = outcomes
    obj.create_provider = Mock(return_value=transport)
    monkeypatch.setattr(pa.time, 'sleep', Mock())
    return obj, transport


def test_empty_response_retries_with_backoff(monkeypatch):
    obj, transport = adapter(monkeypatch, ['  ', 'ok'])
    assert obj.generate_with_fallback('prompt', timeout=7) == 'ok'
    assert transport.generate.call_count == 2
    assert pa.time.sleep.call_count == 1
    timeouts = [c.kwargs['timeout'] for c in transport.generate.call_args_list]
    assert 0 < timeouts[1] <= timeouts[0] <= 7


def test_global_budget_and_official_reserved(monkeypatch):
    plans = [plan(name=f'relay-{i}') for i in range(20)] + [plan('gemini', 'official')]
    obj, transport = adapter(monkeypatch, LLMUpstreamUnavailableError('empty'), plans)
    with pytest.raises(LLMUpstreamUnavailableError):
        obj.generate_with_fallback('prompt')
    assert transport.generate.call_count <= 4
    assert obj.create_provider.call_args.args[0].provider.type == 'gemini'


@pytest.mark.parametrize('error', [ValueError('bad argument'), pa.LLMNonRetryableError('blocked')])
def test_non_retryable_stops(monkeypatch, error):
    obj, transport = adapter(monkeypatch, error, [plan(), plan('gemini', 'official')])
    with pytest.raises(type(error)):
        obj.generate_with_fallback('prompt')
    assert transport.generate.call_count == 1


def test_explicit_official_never_relay(monkeypatch):
    obj, transport = adapter(monkeypatch, LLMUpstreamUnavailableError('empty'),
                             [plan('gemini', 'pro-official'), plan()], 'pro-official')
    with pytest.raises(LLMUpstreamUnavailableError):
        obj.generate_with_fallback('prompt')
    assert all(c.args[0].provider.type == 'gemini' for c in obj.create_provider.call_args_list)


def test_factory_routes_concrete_and_inherited_methods(monkeypatch):
    from src.llm import factory
    from src.llm.vectorengine import VectorEngineProvider
    obj, _ = adapter(monkeypatch, [])
    raw = VectorEngineProvider.__new__(VectorEngineProvider)
    raw.default_model = 'relay'
    raw._build_translation_prompt = Mock(return_value='translate prompt')
    raw._build_deep_analysis_prompt = Mock(return_value='analysis prompt')
    raw._parse_json_response = lambda value: {'parsed': value}
    raw.generate = Mock(side_effect=AssertionError('raw generate bypass'))
    obj.create_provider = Mock(return_value=raw)
    obj.generate_with_fallback = Mock(return_value='ok')
    monkeypatch.setattr(pa, 'get_provider_adapter', lambda alias: obj)
    routed = factory.create_llm_provider('relay')
    assert isinstance(routed, LLMProvider)
    assert routed.translate('source', timeout=9) == 'ok'
    assert routed.deep_analyze('source', 'outline', timeout=8) == {'parsed': 'ok'}
    assert obj.generate_with_fallback.call_args.kwargs['timeout'] == 8
    assert routed is not raw
    raw.generate.assert_not_called()


@pytest.mark.parametrize('provider', [None, 'gemini', 'vectorengine'])
def test_factory_provider_names_use_adapter(monkeypatch, provider):
    from src.llm import factory, config_loader
    model = NS(alias='gemini-pro' if provider != 'gemini' else 'gemini-pro-fallback',
               enabled=True, priority=0, real_model='model')
    loader = Mock()
    loader.get_primary_provider_by_type.return_value = NS(models=[model])
    loader.resolve_config_model_alias.return_value = model.alias
    monkeypatch.setattr(config_loader, 'get_config_loader', lambda: loader)
    monkeypatch.setattr(factory, 'get_task_model_alias', lambda task: model.alias)
    obj = Mock()
    monkeypatch.setattr(pa, 'get_provider_adapter', Mock(return_value=obj))
    assert factory.create_llm_provider(provider) is obj.as_llm_provider.return_value


def test_gemini_adapter_attempt_does_not_expand_internal_plan(monkeypatch):
    from src.llm import gemini as gm
    obj = gm.GeminiProvider.__new__(gm.GeminiProvider)
    obj.model_name, obj.backup_model, obj.api_keys = 'model', 'backup', ['fake', 'fake2']
    obj.max_attempts, obj.request_timeout = 99, 19
    obj._build_attempt_plan = Mock(return_value=[NS(model_name='model', key_role='test', api_key='fake')] * 5)
    obj._use_rest_transport = lambda: True
    obj._generate_once = Mock(side_effect=LLMUpstreamUnavailableError('empty'))
    obj._normalize_generation_exception = lambda exc, **kw: exc
    obj._error_to_text = str
    obj._is_non_retryable_error = lambda text: False
    obj._is_retryable_error = lambda text: True
    monkeypatch.setattr(gm.llm_usage_metrics, 'record_call', Mock(return_value=1))
    with pytest.raises(LLMUpstreamUnavailableError):
        obj.generate('prompt', _single_attempt=True, timeout=6, max_retries=90)
    assert obj._generate_once.call_count == 1
    assert 0 < obj._generate_once.call_args.kwargs['timeout'] <= 6
    gm.llm_usage_metrics.record_call.assert_called_once()


def test_gemini_empty_is_failed_usage(monkeypatch):
    from src.llm import gemini as gm
    obj = gm.GeminiProvider.__new__(gm.GeminiProvider)
    obj.model_name, obj.backup_model, obj.api_keys = 'model', None, ['fake']
    obj.max_attempts, obj.request_timeout = 1, 9
    obj._build_attempt_plan = lambda model: [NS(model_name=model, key_role='test')]
    obj._use_rest_transport = lambda: True
    obj._generate_once = Mock(return_value=gm.GeminiGenerationResult(
        text=' ', input_tokens=11, output_tokens=3, total_tokens=14))
    record = Mock(return_value=1)
    monkeypatch.setattr(gm.llm_usage_metrics, 'record_call', record)
    with pytest.raises(LLMUpstreamUnavailableError):
        obj.generate('prompt', _single_attempt=True)
    record.assert_called_once()
    assert record.call_args.kwargs['success'] is False
    assert record.call_args.kwargs['total_tokens'] == 14


def test_legacy_constructor_settings_still_route(monkeypatch):
    from src.llm import factory
    from src.llm.vectorengine import VectorEngineProvider
    raw = VectorEngineProvider.__new__(VectorEngineProvider)
    raw.default_model = 'custom-model'
    raw.generate = Mock(side_effect=['', 'ok'])
    construct = Mock(return_value=raw)
    monkeypatch.setattr(factory, 'USE_NEW_CONFIG', False)
    monkeypatch.setitem(factory._PROVIDER_FACTORIES, 'vectorengine', construct)
    monkeypatch.setattr(factory, 'get_model_provider', lambda name: 'vectorengine')
    monkeypatch.setattr(pa.time, 'sleep', Mock())
    routed = factory.create_llm_provider('vectorengine', api_key='fake', timeout=13)
    assert routed.generate('prompt', timeout=5) == 'ok'
    assert raw.generate.call_count == 2
    assert construct.call_args.kwargs['api_key'] == 'fake'


def test_sdk_retries_are_disabled():
    from contextlib import nullcontext
    from src.llm.gemini import GeminiProvider
    obj = GeminiProvider.__new__(GeminiProvider)
    client = Mock()
    client.models.generate_content.return_value = NS(text='ok', usage_metadata=None)
    obj._use_rest_transport = lambda: False
    obj._get_client = lambda key: client
    obj._resolve_max_output_tokens = lambda: 100
    obj._temporary_proxy_env = nullcontext
    obj._generate_with_timeout_fn = lambda fn, timeout: fn()
    obj._generate_once(prompt='prompt', attempt=NS(api_key='fake', model_name='model'),
                       timeout=5, temperature=.3, response_mime_type=None)
    options = client.models.generate_content.call_args.kwargs['config']['http_options']
    assert options['retry_options']['attempts'] == 1
    assert options['timeout'] > 0


def test_openai_server_error_is_retryable(monkeypatch):
    import httpx
    from openai import InternalServerError
    error = InternalServerError('server error', response=httpx.Response(
        500, request=httpx.Request('POST', 'https://offline.invalid')), body=None)
    obj, transport = adapter(monkeypatch, [error, 'ok'])
    assert obj.generate_with_fallback('prompt') == 'ok'
    assert transport.generate.call_count == 2


@pytest.mark.parametrize('status', [400, 401, 403, 404, 422])
def test_http_client_errors_not_retried_even_with_transient_words(monkeypatch, status):
    import httpx
    from openai import APIStatusError
    error = APIStatusError('upstream timeout invalid argument', response=httpx.Response(
        status, request=httpx.Request('POST', 'https://offline.invalid')), body=None)
    obj, transport = adapter(monkeypatch, [error, 'should not happen'])
    with pytest.raises(APIStatusError):
        obj.generate_with_fallback('prompt')
    assert transport.generate.call_count == 1


def test_real_openai_sdk_has_no_hidden_requests(monkeypatch):
    import httpx
    from openai import OpenAI
    from src.llm import vectorengine as ve
    requests = []
    def respond(request):
        requests.append(request)
        return httpx.Response(500, json={'error': {'message': 'server error'}})
    with httpx.Client(transport=httpx.MockTransport(respond)) as http:
        obj = ve.VectorEngineProvider.__new__(ve.VectorEngineProvider)
        obj.default_model, obj.temperature, obj.max_tokens = 'relay', .3, 100
        obj.timeout, obj.max_retries = 17, 9
        obj.client = OpenAI(api_key='fake', base_url='https://offline.invalid/v1',
                            http_client=http, max_retries=9)
        record = Mock()
        monkeypatch.setattr(ve.llm_usage_metrics, 'record_call', record)
        monkeypatch.setattr(pa.time, 'sleep', Mock())
        routed = pa.ProviderAdapter.from_provider(obj, 'vectorengine', 'relay').as_llm_provider()
        with pytest.raises(LLMUpstreamUnavailableError):
            routed.generate('prompt')
        assert len(requests) == 2
        assert record.call_count == 2
        assert all(c.kwargs['success'] is False for c in record.call_args_list)


@pytest.mark.parametrize('content', [None, '', '  ', 'ok'])
def test_vectorengine_each_response_accounted_once(monkeypatch, content):
    from src.llm import vectorengine as ve
    obj = ve.VectorEngineProvider.__new__(ve.VectorEngineProvider)
    obj.default_model, obj.temperature, obj.max_tokens = 'relay', .3, 100
    obj.timeout, obj.max_retries = 17, 9
    obj.client = Mock()
    obj.client.with_options.return_value = obj.client
    obj.client.chat.completions.create.return_value = NS(
        choices=[NS(message=NS(content=content))],
        usage=NS(prompt_tokens=11, completion_tokens=3, total_tokens=14))
    record = Mock()
    monkeypatch.setattr(ve.llm_usage_metrics, 'record_call', record)
    if content == 'ok':
        assert obj.generate('prompt') == 'ok'
    else:
        with pytest.raises(LLMUpstreamUnavailableError):
            obj.generate('prompt')
    record.assert_called_once()
    data = record.call_args.kwargs
    assert data['success'] is (content == 'ok')
    assert data['input_tokens'] == 11 and data['total_tokens'] == 14
    if content != 'ok':
        assert data['error_type'] == 'LLMUpstreamUnavailableError'
    assert obj.client.with_options.call_args.kwargs['max_retries'] == 0
