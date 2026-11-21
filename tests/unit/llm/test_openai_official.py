"""Official model integration, transport identity and selection regressions."""
import json
from pathlib import Path

import httpx
import pytest
from openai import OpenAI

from src.llm.config_loader import ConfigLoader
from src.llm.fallback_strategy import FallbackStrategy
from src.llm.provider_adapter import ProviderAdapter
from src.llm.errors import LLMConfigurationError, LLMUpstreamUnavailableError

MODEL = 'gpt-6.1-sol'
ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def loader(monkeypatch):
    for name in ('OPENAI_API_KEY', 'GEMINI_API_KEY', 'VECTORENGINE_API_KEY', 'DEEPSEEK_API_KEY'):
        monkeypatch.setenv(name, 'test-not-a-secret')
    obj = ConfigLoader(str(ROOT / 'config/llm_providers.yaml'))
    monkeypatch.setattr('src.llm.provider_adapter.get_config_loader', lambda: obj)
    monkeypatch.setattr('src.llm.config_loader.get_config_loader', lambda: obj)
    from src.llm.provider_adapter import get_provider_adapter
    get_provider_adapter.cache_clear()
    yield obj
    get_provider_adapter.cache_clear()


def test_catalog_and_defaults(loader):
    from src.api.routers.models import _list_models_sync
    from src.core.model_config import ModelConfig
    config = loader.load()
    assert config.task_defaults == {'longform':'gemini-flash','post':'gpt-6.2-sol',
        'post_optimize':'gemini-official-argon','analysis':'deepseek-v3','title':'gemini-official-argon',
        'metadata':'deepseek-v3','slack':'gpt-6.2-sol'}
    official = config.providers['openai-official']
    assert official.type == 'openai' and official.relay is False
    assert official.api_keys[0].key == 'test-not-a-secret'
    assert not official.allow_cross_provider_fallback
    listed = next(p for p in _list_models_sync().providers if p.id == 'openai-official')
    assert config.task_fallbacks == {'post': 'gemini-flash'}
    assert [m.real_model for m in listed.models] == [MODEL, 'gpt-6.2-sol']
    assert all(m.available and 'OpenAI 官方' in m.name for m in listed.models)
    for filename in ('llm_providers.yaml', 'llm_providers.yaml.example'):
        cfg = ConfigLoader(str(ROOT / 'config' / filename)).load()
        plans = FallbackStrategy(cfg).build_attempt_plan(MODEL)
        assert plans and all(p.provider.provider_id == 'openai-official' and p.model.real_model == MODEL for p in plans)
        assert all(p.model.real_model != MODEL for p in FallbackStrategy(cfg).build_attempt_plan('gemini-flash'))
    phases = ModelConfig(str(ROOT / 'config/translation_models.yaml'))
    assert MODEL in phases.get_available_models()
    for phase in ('phase0_prescan','phase1_draft','phase2_refine','phase3_review'):
        assert phases.get_model_for_phase(phase, MODEL)['model'] == MODEL


def install_transport(monkeypatch, handler):
    def client(**kwargs):
        kwargs['http_client'].close()
        kwargs['http_client'] = httpx.Client(transport=httpx.MockTransport(handler))
        return OpenAI(**kwargs)
    monkeypatch.setattr('src.llm.openai_official.OpenAI', client)


def response(text='好的', model=MODEL, finish='stop'):
    return {'id':'chatcmpl-test', 'object':'chat.completion', 'created':0, 'model':model,
            'choices':[{'index':0,'message':{'role':'assistant','content':text},'finish_reason':finish}],
            'usage':{'prompt_tokens':2,'completion_tokens':2,'total_tokens':4}}


def test_real_factory_and_phase_transport(loader, monkeypatch):
    from src.llm.factory import create_llm_provider
    from src.llm.phase_provider import phase_provider
    calls = []
    def handler(req):
        calls.append(json.loads(req.content))
        assert str(req.url) == 'https://api.openai.com/v1/chat/completions'
        return httpx.Response(200, json=response())
    install_transport(monkeypatch, handler)
    provider = phase_provider(create_llm_provider(MODEL), {'temperature':0.3,'max_tokens':64,'timeout':10})
    metadata = {}
    assert provider.generate('只回复好的', response_format='json', result_metadata=metadata) == '好的'
    assert calls == [{'model':MODEL,'messages':[{'role':'user','content':'只回复好的'}],
                      'max_completion_tokens':64,'store':False,'response_format':{'type':'json_object'}}]
    assert metadata['provider_used'] == 'openai-official'
    assert metadata['model_used'] == metadata['real_model_used'] == MODEL
    assert metadata['fallback_used'] is False


@pytest.mark.parametrize('status,count', [(400,1),(401,1),(429,2),(503,2)])
def test_error_does_not_switch_brand_or_leak_body(loader, monkeypatch, caplog, status, count):
    calls = []
    def handler(req):
        calls.append(str(req.url))
        return httpx.Response(status,json={'error':{'message':'sk-proj-secret-body upstream timeout','type':'error','code':'error'}})
    install_transport(monkeypatch, handler)
    with pytest.raises((LLMConfigurationError, LLMUpstreamUnavailableError)) as exc:
        ProviderAdapter(MODEL).generate_with_fallback('hello',timeout=10)
    assert len(calls) == count
    assert all(url.startswith('https://api.openai.com/') for url in calls)
    assert 'sk-proj-secret-body' not in str(exc.value) + caplog.text


@pytest.mark.parametrize('payload', [response(''), response(model='another-model'), response(finish='length')])
def test_invalid_generation_is_not_success(loader, monkeypatch, payload):
    install_transport(monkeypatch, lambda req: httpx.Response(200,json=payload))
    metadata = {}
    with pytest.raises(Exception):
        ProviderAdapter(MODEL).generate_with_fallback('hello', result_metadata=metadata, timeout=10)
    assert not metadata


def test_missing_key_cannot_fallback(loader, monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY')
    loader._config = None
    with pytest.raises(ValueError,match='No valid attempt plan'):
        ProviderAdapter(MODEL)
