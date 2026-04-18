"""
Runtime network policy resolution for LLM providers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .config_models import ProviderNetworkConfig


@dataclass(frozen=True)
class RuntimeNetworkPolicy:
    provider_type: str
    proxy_mode: str
    use_proxy: bool
    trust_env: bool
    proxies: Optional[dict[str, str]]
    no_proxy: Optional[str]


def _clean(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def build_network_policy(
    provider_type: str,
    cfg: ProviderNetworkConfig,
) -> RuntimeNetworkPolicy:
    proxy_mode = (cfg.proxy_mode or "env").strip().lower() or "env"
    provider_type = provider_type.strip().lower()
    no_proxy = _clean(cfg.no_proxy)

    if proxy_mode == "required":
        http_proxy = _clean(cfg.http_proxy)
        https_proxy = _clean(cfg.https_proxy) or http_proxy
        if not http_proxy and not https_proxy:
            raise ValueError(f"{provider_type} requires proxy configuration")
        return RuntimeNetworkPolicy(
            provider_type=provider_type,
            proxy_mode=proxy_mode,
            use_proxy=True,
            trust_env=False,
            proxies={
                "http": http_proxy or https_proxy,
                "https": https_proxy or http_proxy,
            },
            no_proxy=no_proxy,
        )

    if proxy_mode == "disabled":
        return RuntimeNetworkPolicy(
            provider_type=provider_type,
            proxy_mode=proxy_mode,
            use_proxy=False,
            trust_env=False,
            proxies=None,
            no_proxy=no_proxy,
        )

    return RuntimeNetworkPolicy(
        provider_type=provider_type,
        proxy_mode="env",
        use_proxy=False,
        trust_env=True,
        proxies=None,
        no_proxy=no_proxy,
    )
