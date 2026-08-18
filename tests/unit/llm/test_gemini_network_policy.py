"""Regression tests for Gemini transport network-policy enforcement."""

from types import SimpleNamespace

from src.llm.gemini import GeminiProvider
from src.llm.network_policy import RuntimeNetworkPolicy


def _provider_for_policy(policy: RuntimeNetworkPolicy) -> GeminiProvider:
    provider = GeminiProvider.__new__(GeminiProvider)
    provider.network_policy = policy
    provider.proxy_config = None
    return provider


def _direct_policy() -> RuntimeNetworkPolicy:
    return RuntimeNetworkPolicy(
        provider_type="gemini",
        proxy_mode="disabled",
        use_proxy=False,
        trust_env=False,
        proxies=None,
        no_proxy=None,
    )


def test_disabled_proxy_mode_forces_sdk_to_ignore_proxy_environment():
    captured = {}

    def client(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace()

    provider = _provider_for_policy(_direct_policy())
    provider._create_client(SimpleNamespace(Client=client), "test-key")

    assert captured["api_key"] == "test-key"
    assert captured["http_options"] == {
        "client_args": {"trust_env": False},
        "async_client_args": {"trust_env": False},
    }


def test_disabled_proxy_mode_forces_rest_to_ignore_proxy_environment():
    provider = _provider_for_policy(_direct_policy())

    session = provider._build_rest_session()
    try:
        assert session.trust_env is False
    finally:
        session.close()
