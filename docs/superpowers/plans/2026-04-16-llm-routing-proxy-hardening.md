# LLM Routing And Proxy Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify all LLM call paths behind one fallback pipeline, move provider proxy strategy into YAML, force Gemini through proxy, force VectorEngine direct-connect, and standardize timeout/error/logging behavior.

**Architecture:** The app will resolve every task or explicit model request to one canonical YAML model alias, then execute through `ProviderAdapter` and `FallbackStrategy`. Provider-specific network behavior will come from YAML `network` config and be enforced by a shared runtime policy layer. API routes will stop inferring provider-specific failures from raw strings and instead consume normalized LLM error types.

**Tech Stack:** FastAPI, Pydantic settings/models, YAML config loader, google-genai/REST Gemini client, OpenAI-compatible VectorEngine client, pytest.

---

## File Map

**Create**
- `src/llm/network_policy.py` — Parse provider `network` config into runtime-enforced transport/proxy policy.
- `src/llm/errors.py` — Shared LLM error taxonomy and helper constructors.
- `tests/unit/llm/test_network_policy.py` — Unit tests for proxy strategy resolution.
- `tests/unit/llm/test_llm_routing.py` — Unit tests for default task routing through `ProviderAdapter`.
- `tests/unit/llm/test_llm_error_mapping.py` — Unit tests for provider error normalization.
- `tests/integration/test_llm_fallback_chain.py` — Integration-level coverage for Gemini failure → VectorEngine fallback.

**Modify**
- `config/llm_providers.yaml` — Remove hardcoded key, add `network` blocks, normalize defaults.
- `.env.example` — Document provider keys and Gemini-specific proxy vars.
- `src/llm/config_models.py` — Add provider network config models.
- `src/llm/config_loader.py` — Parse and validate `network` config.
- `src/llm/factory.py` — Resolve all task defaults to canonical aliases for adapter execution.
- `src/api/utils/llm_factory.py` — Route all requests, including default task paths, through adapter/fallback.
- `src/llm/provider_adapter.py` — Pass timeout, network policy, and normalized request metadata into providers.
- `src/llm/fallback_strategy.py` — Keep canonical alias resolution as the single source of truth.
- `src/llm/gemini.py` — Enforce YAML-driven proxy-required networking and normalize upstream errors.
- `src/llm/vectorengine.py` — Enforce proxy-disabled networking and normalize upstream errors.
- `src/config.py` — Remove routing ambiguity, add optional Gemini proxy env vars for YAML interpolation.
- `src/api/routers/translate_posts.py` — Replace stringly provider-specific error formatting with normalized LLM exceptions.
- `tests/test_llm_config_system.py` — Extend coverage for canonical alias resolution and config-backed provider creation.

**Docs**
- `README.md` — Brief operator notes about provider/proxy behavior and fallback expectations.

---

### Task 1: Harden Config Schema And Remove Secret Footguns

**Files:**
- Modify: `config/llm_providers.yaml`
- Modify: `.env.example`
- Modify: `src/llm/config_models.py`
- Modify: `src/llm/config_loader.py`
- Test: `tests/test_llm_config_system.py`

- [ ] **Step 1: Write the failing config tests**

```python
def test_provider_network_config_is_loaded():
    from src.llm.config_loader import reset_config_loader, get_config_loader

    reset_config_loader()
    config = get_config_loader().load()

    assert config.providers["gemini-official"].network.proxy_mode == "required"
    assert config.providers["vectorengine-relay"].network.proxy_mode == "disabled"


def test_hardcoded_vectorengine_key_is_not_present():
    from pathlib import Path

    text = Path("config/llm_providers.yaml").read_text(encoding="utf-8")
    assert "sk-" not in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_llm_config_system.py -q`
Expected: FAIL because `ProviderConfig` has no `network` attribute and/or YAML still contains a hardcoded VectorEngine key.

- [ ] **Step 3: Add network config models and loader support**

```python
# src/llm/config_models.py
from typing import Optional, Literal
from pydantic import BaseModel, Field


class ProviderNetworkConfig(BaseModel):
    proxy_mode: Literal["required", "disabled", "env"] = "env"
    http_proxy: Optional[str] = None
    https_proxy: Optional[str] = None
    no_proxy: Optional[str] = None


class ProviderConfig(BaseModel):
    ...
    network: ProviderNetworkConfig = Field(default_factory=ProviderNetworkConfig)
```

```python
# src/llm/config_loader.py
network = ProviderNetworkConfig(**data.get("network", {}))

return ProviderConfig(
    ...,
    network=network,
)
```

```yaml
# config/llm_providers.yaml
gemini-official:
  network:
    proxy_mode: required
    http_proxy: "${GEMINI_HTTP_PROXY}"
    https_proxy: "${GEMINI_HTTPS_PROXY}"
    no_proxy: "${GEMINI_NO_PROXY}"

vectorengine-relay:
  network:
    proxy_mode: disabled
  api_keys:
    - key: "${VECTORENGINE_API_KEY}"
      priority: 1
      name: "主 Key"
```

- [ ] **Step 4: Update operator-facing env examples**

```env
# .env.example
GEMINI_API_KEY=
GEMINI_BACKUP_API_KEY=
GEMINI_HTTP_PROXY=http://127.0.0.1:7897
GEMINI_HTTPS_PROXY=http://127.0.0.1:7897
GEMINI_NO_PROXY=localhost,127.0.0.1

VECTORENGINE_API_KEY=
VECTORENGINE_BASE_URL=https://api.vectorengine.ai/v1
```

- [ ] **Step 5: Run tests to verify config parsing passes**

Run: `pytest tests/test_llm_config_system.py -q`
Expected: PASS for network parsing and no hardcoded key.

- [ ] **Step 6: Commit**

```bash
git add config/llm_providers.yaml .env.example src/llm/config_models.py src/llm/config_loader.py tests/test_llm_config_system.py
git commit -m "refactor: move provider network policy into llm config"
```

---

### Task 2: Add Runtime Network Policy Enforcement

**Files:**
- Create: `src/llm/network_policy.py`
- Modify: `src/config.py`
- Test: `tests/unit/llm/test_network_policy.py`

- [ ] **Step 1: Write the failing network policy tests**

```python
from src.llm.config_models import ProviderNetworkConfig
from src.llm.network_policy import build_network_policy


def test_required_proxy_provider_requires_proxy_values():
    cfg = ProviderNetworkConfig(proxy_mode="required")

    try:
        build_network_policy("gemini", cfg)
    except ValueError as exc:
        assert "proxy" in str(exc).lower()
    else:
        raise AssertionError("expected ValueError")


def test_disabled_proxy_provider_disables_env_proxy_inheritance():
    cfg = ProviderNetworkConfig(proxy_mode="disabled")
    policy = build_network_policy("vectorengine", cfg)

    assert policy.use_proxy is False
    assert policy.trust_env is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/llm/test_network_policy.py -q`
Expected: FAIL because `build_network_policy` does not exist.

- [ ] **Step 3: Implement the shared network policy module**

```python
# src/llm/network_policy.py
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


def build_network_policy(provider_type: str, cfg: ProviderNetworkConfig) -> RuntimeNetworkPolicy:
    if cfg.proxy_mode == "required":
        proxies = {
            "http": (cfg.http_proxy or "").strip(),
            "https": (cfg.https_proxy or cfg.http_proxy or "").strip(),
        }
        if not proxies["http"] and not proxies["https"]:
            raise ValueError(f"{provider_type} requires proxy configuration")
        return RuntimeNetworkPolicy(provider_type, "required", True, False, proxies, cfg.no_proxy)

    if cfg.proxy_mode == "disabled":
        return RuntimeNetworkPolicy(provider_type, "disabled", False, False, None, cfg.no_proxy)

    return RuntimeNetworkPolicy(provider_type, "env", False, True, None, cfg.no_proxy)
```

- [ ] **Step 4: Add optional settings fields for YAML env interpolation only**

```python
# src/config.py
gemini_http_proxy: str = ""
gemini_https_proxy: str = ""
gemini_no_proxy: str = ""
```

- [ ] **Step 5: Run tests to verify runtime policy logic passes**

Run: `pytest tests/unit/llm/test_network_policy.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/llm/network_policy.py src/config.py tests/unit/llm/test_network_policy.py
git commit -m "feat: add provider network policy enforcement"
```

---

### Task 3: Route Every LLM Request Through ProviderAdapter

**Files:**
- Modify: `src/api/utils/llm_factory.py`
- Modify: `src/llm/factory.py`
- Test: `tests/unit/llm/test_llm_routing.py`

- [ ] **Step 1: Write the failing routing tests**

```python
from unittest.mock import MagicMock, patch

from src.api.utils.llm_factory import generate_with_fallback


@patch("src.api.utils.llm_factory.get_provider_adapter")
@patch("src.api.utils.llm_factory.get_llm_provider_for_task")
def test_default_task_routing_uses_adapter_not_direct_provider(mock_task_provider, mock_get_adapter):
    mock_task_provider.return_value = MagicMock()
    adapter = MagicMock()
    adapter.generate_with_fallback.return_value = "ok"
    mock_get_adapter.return_value = adapter

    result = generate_with_fallback("prompt", task_type="post")

    assert result == "ok"
    adapter.generate_with_fallback.assert_called_once()
    mock_task_provider.return_value.generate.assert_not_called()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/llm/test_llm_routing.py -q`
Expected: FAIL because default task routing still calls provider `.generate(...)` directly.

- [ ] **Step 3: Refactor routing to always resolve a canonical alias**

```python
# src/llm/factory.py
def get_task_model_alias(task_type: str) -> str:
    if USE_NEW_CONFIG:
        ...
        if model_alias:
            return model_alias
    ...
    return task_model_map.get(task_type, settings.llm_default_model)
```

```python
# src/api/utils/llm_factory.py
from ...llm.factory import get_task_model_alias
from ...llm.provider_adapter import get_provider_adapter


def generate_with_fallback(...):
    target_model = model or get_task_model_alias(task_type)
    adapter = get_provider_adapter(target_model)
    return adapter.generate_with_fallback(
        prompt=prompt,
        timeout=timeout,
        **kwargs,
    )
```

- [ ] **Step 4: Remove the direct-provider default path**

```python
# src/api/utils/llm_factory.py
# delete:
# provider = get_llm_provider_for_task(task_type)
# return provider.generate(...)
```

- [ ] **Step 5: Run tests to verify default paths now use adapter**

Run: `pytest tests/unit/llm/test_llm_routing.py tests/test_llm_config_system.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/api/utils/llm_factory.py src/llm/factory.py tests/unit/llm/test_llm_routing.py tests/test_llm_config_system.py
git commit -m "refactor: route all llm requests through provider adapter"
```

---

### Task 4: Make ProviderAdapter Pass Timeout And Network Policy

**Files:**
- Modify: `src/llm/provider_adapter.py`
- Modify: `src/llm/gemini.py`
- Modify: `src/llm/vectorengine.py`
- Test: `tests/unit/llm/test_llm_routing.py`

- [ ] **Step 1: Write the failing timeout propagation test**

```python
from unittest.mock import MagicMock, patch


@patch("src.llm.provider_adapter.ProviderAdapter.create_provider")
def test_adapter_passes_timeout_to_provider(mock_create_provider):
    from src.llm.provider_adapter import get_provider_adapter

    provider = MagicMock()
    provider.generate.return_value = "ok"
    mock_create_provider.return_value = provider

    adapter = get_provider_adapter("flash-official")
    adapter.generate_with_fallback(prompt="hello", timeout=19)

    assert provider.generate.call_args.kwargs["timeout"] == 19
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/llm/test_llm_routing.py -q`
Expected: FAIL because adapter currently drops `timeout`.

- [ ] **Step 3: Thread runtime policy and timeout through adapter**

```python
# src/llm/provider_adapter.py
from .network_policy import build_network_policy

policy = build_network_policy(provider_config.type, provider_config.network)
provider = self.create_provider(attempt, policy=policy)

result = provider.generate(
    prompt=prompt,
    response_format=response_format,
    temperature=temperature,
    model=attempt.model.real_model,
    timeout=kwargs.get("timeout"),
    **other_kwargs,
)
```

- [ ] **Step 4: Update provider constructors to accept network policy**

```python
# src/llm/gemini.py / src/llm/vectorengine.py
def __init__(..., network_policy=None):
    self.network_policy = network_policy
```

- [ ] **Step 5: Run tests to verify timeout propagation works**

Run: `pytest tests/unit/llm/test_llm_routing.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/llm/provider_adapter.py src/llm/gemini.py src/llm/vectorengine.py tests/unit/llm/test_llm_routing.py
git commit -m "refactor: propagate timeout and network policy through llm adapter"
```

---

### Task 5: Enforce Gemini Proxy-Required Transport

**Files:**
- Modify: `src/llm/gemini.py`
- Create: `tests/unit/llm/test_llm_error_mapping.py`
- Test: `tests/unit/llm/test_network_policy.py`

- [ ] **Step 1: Write the failing Gemini proxy enforcement tests**

```python
from src.llm.network_policy import RuntimeNetworkPolicy
from src.llm.gemini import GeminiProvider


def test_gemini_required_proxy_without_proxy_fails_fast():
    policy = RuntimeNetworkPolicy(
        provider_type="gemini",
        proxy_mode="required",
        use_proxy=True,
        trust_env=False,
        proxies=None,
        no_proxy=None,
    )

    try:
        GeminiProvider(api_key="x", model="gemini-flash-latest", network_policy=policy)
    except ValueError as exc:
        assert "proxy" in str(exc).lower()
    else:
        raise AssertionError("expected proxy configuration failure")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/llm/test_network_policy.py tests/unit/llm/test_llm_error_mapping.py -q`
Expected: FAIL because Gemini does not enforce proxy-required config.

- [ ] **Step 3: Move Gemini transport selection behind explicit policy**

```python
# src/llm/gemini.py
def _resolve_transport_mode(self) -> str:
    if self.network_policy and self.network_policy.proxy_mode == "required":
        return "rest"
    override = os.getenv("GEMINI_USE_REST")
    ...


def _validate_network_policy(self) -> None:
    if self.network_policy and self.network_policy.proxy_mode == "required":
        if not self.network_policy.proxies:
            raise ValueError("Gemini provider requires proxy configuration")
```

```python
# src/llm/gemini.py
response = requests.post(
    url,
    json=payload,
    headers=headers,
    timeout=request_timeout,
    proxies=self.network_policy.proxies,
)
```

- [ ] **Step 4: Normalize Gemini transport errors**

```python
# src/llm/errors.py
class LLMProxyError(Exception): ...
class LLMTLSError(Exception): ...
class LLMTimeoutError(Exception): ...
class LLMUpstreamUnavailableError(Exception): ...
```

```python
# src/llm/gemini.py
except requests.exceptions.ProxyError as exc:
    raise LLMProxyError(str(exc)) from exc
except requests.exceptions.SSLError as exc:
    raise LLMTLSError(str(exc)) from exc
except requests.exceptions.Timeout as exc:
    raise LLMTimeoutError(str(exc)) from exc
```

- [ ] **Step 5: Run tests to verify Gemini now honors required proxy policy**

Run: `pytest tests/unit/llm/test_network_policy.py tests/unit/llm/test_llm_error_mapping.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/llm/gemini.py src/llm/errors.py tests/unit/llm/test_network_policy.py tests/unit/llm/test_llm_error_mapping.py
git commit -m "feat: enforce proxy-required transport for gemini provider"
```

---

### Task 6: Enforce VectorEngine Direct-Connect Transport

**Files:**
- Modify: `src/llm/vectorengine.py`
- Test: `tests/unit/llm/test_network_policy.py`

- [ ] **Step 1: Write the failing VectorEngine direct-connect test**

```python
from src.llm.network_policy import RuntimeNetworkPolicy
from src.llm.vectorengine import VectorEngineProvider


def test_vectorengine_disabled_proxy_turns_off_env_proxy_inheritance():
    policy = RuntimeNetworkPolicy(
        provider_type="vectorengine",
        proxy_mode="disabled",
        use_proxy=False,
        trust_env=False,
        proxies=None,
        no_proxy=None,
    )

    provider = VectorEngineProvider(
        api_key="key",
        base_url="https://api.vectorengine.ai/v1",
        model="deepseek-v3.2",
        network_policy=policy,
    )

    assert provider.network_policy.trust_env is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/llm/test_network_policy.py -q`
Expected: FAIL because VectorEngine provider does not yet enforce proxy-disabled behavior.

- [ ] **Step 3: Build VectorEngine client with proxy inheritance disabled**

```python
# src/llm/vectorengine.py
import httpx
from openai import OpenAI

transport_client = httpx.Client(
    timeout=self.timeout,
    trust_env=self.network_policy.trust_env if self.network_policy else True,
)

self.client = OpenAI(
    api_key=self.api_key,
    base_url=self.base_url,
    timeout=self.timeout,
    max_retries=self.max_retries,
    http_client=transport_client,
)
```

- [ ] **Step 4: Normalize VectorEngine network errors**

```python
# src/llm/vectorengine.py
except APITimeoutError as exc:
    raise LLMTimeoutError(str(exc)) from exc
except APIError as exc:
    raise LLMUpstreamUnavailableError(str(exc)) from exc
```

- [ ] **Step 5: Run tests to verify VectorEngine now ignores env proxy**

Run: `pytest tests/unit/llm/test_network_policy.py tests/unit/llm/test_llm_error_mapping.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/llm/vectorengine.py tests/unit/llm/test_network_policy.py tests/unit/llm/test_llm_error_mapping.py
git commit -m "feat: force direct network path for vectorengine provider"
```

---

### Task 7: Normalize API Error Handling And Logging

**Files:**
- Modify: `src/api/routers/translate_posts.py`
- Modify: `src/llm/provider_adapter.py`
- Modify: `src/llm/gemini.py`
- Modify: `src/llm/vectorengine.py`
- Test: `tests/unit/llm/test_llm_error_mapping.py`

- [ ] **Step 1: Write the failing API error mapping tests**

```python
from src.llm.errors import LLMProxyError
from src.api.routers.translate_posts import _format_generation_error


def test_translate_post_formats_proxy_error_without_vendor_string_matching():
    text = _format_generation_error(LLMProxyError("proxy down"), "Translation", 60)
    assert "proxy" in text.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/llm/test_llm_error_mapping.py -q`
Expected: FAIL because API route formatting still relies on raw string parsing.

- [ ] **Step 3: Replace string matching with typed LLM exceptions**

```python
# src/api/routers/translate_posts.py
from src.llm.errors import (
    LLMProxyError,
    LLMTLSError,
    LLMTimeoutError,
    LLMUpstreamUnavailableError,
)

if isinstance(exc, LLMProxyError):
    ...
if isinstance(exc, LLMTLSError):
    ...
```

- [ ] **Step 4: Add structured adapter logs**

```python
# src/llm/provider_adapter.py
logger.info(
    "[LLM Attempt] request_model=%s resolved_model=%s provider=%s real_model=%s attempt=%s/%s",
    self.model_alias,
    attempt.model.alias,
    attempt.provider.provider_id,
    attempt.model.real_model,
    idx,
    len(self.attempt_plan),
)
```

- [ ] **Step 5: Run tests to verify normalized error mapping**

Run: `pytest tests/unit/llm/test_llm_error_mapping.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/api/routers/translate_posts.py src/llm/provider_adapter.py src/llm/gemini.py src/llm/vectorengine.py tests/unit/llm/test_llm_error_mapping.py
git commit -m "refactor: normalize llm error mapping and attempt logging"
```

---

### Task 8: Validate The Full Fallback Chain

**Files:**
- Create: `tests/integration/test_llm_fallback_chain.py`
- Modify: `README.md`

- [ ] **Step 1: Write the failing integration test**

```python
from unittest.mock import patch

from src.api.utils.llm_factory import generate_with_fallback
from src.llm.errors import LLMTLSError


def test_flash_official_falls_back_to_vectorengine_when_gemini_tls_fails():
    with patch("src.llm.gemini.GeminiProvider.generate", side_effect=LLMTLSError("eof")), \
         patch("src.llm.vectorengine.VectorEngineProvider.generate", return_value="OK"):
        result = generate_with_fallback("hello", model="flash-official", timeout=20)

    assert result == "OK"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_llm_fallback_chain.py -q`
Expected: FAIL until the full adapter/provider/error path is wired correctly.

- [ ] **Step 3: Add operator docs**

```md
# README.md
- Gemini official provider obeys YAML `network.proxy_mode=required` and must have proxy config.
- VectorEngine obeys YAML `network.proxy_mode=disabled` and ignores env proxy inheritance.
- All default task paths now execute through the shared fallback chain.
```

- [ ] **Step 4: Run the focused regression suite**

Run: `pytest tests/test_llm_config_system.py tests/unit/llm/test_network_policy.py tests/unit/llm/test_llm_routing.py tests/unit/llm/test_llm_error_mapping.py tests/integration/test_llm_fallback_chain.py -q`
Expected: PASS

- [ ] **Step 5: Smoke-test the live API locally**

Run:
```bash
python - <<'PY'
import requests

body = {"content": "Hello world", "model": "flash-official"}
resp = requests.post("http://127.0.0.1:54321/api/translate/post", json=body, timeout=60)
print(resp.status_code)
print(resp.text)
PY
```

Expected: `200` plus a translated response. When Gemini proxy is intentionally broken, expected behavior is a successful response via VectorEngine fallback rather than immediate `503`.

- [ ] **Step 6: Commit**

```bash
git add tests/integration/test_llm_fallback_chain.py README.md
git commit -m "test: cover full llm fallback chain and document network policy"
```

---

## Self-Review

- Spec coverage: covers config schema, routing unification, provider transport policy, timeout propagation, error taxonomy, observability, and end-to-end validation.
- Placeholder scan: no `TODO`/`TBD` placeholders remain in tasks.
- Type consistency: all tasks refer to `ProviderNetworkConfig`, `RuntimeNetworkPolicy`, and adapter-driven execution consistently.

