"""Run-local provider facades with explicit phase-owned generation settings."""
from copy import copy
from types import MethodType
import math


def phase_provider(provider, config: dict):
    options = {key: config[key] for key in ("temperature", "max_tokens", "timeout") if key in config}
    if "temperature" in options:
        value = options["temperature"]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 2:
            raise ValueError("Phase temperature must be finite and between 0 and 2")
    from .execution_context import positive_timeout, positive_token_limit
    if "timeout" in options:
        positive_timeout(options["timeout"])
    if "max_tokens" in options:
        positive_token_limit(options["max_tokens"])
    # Test doubles and plugins without a generation seam still work. Their
    # explicit business methods remain responsible for their own configuration.
    if not callable(getattr(provider, "generate", None)):
        return provider
    facade = copy(provider)
    facade._phase_config = dict(options)
    facade._request_budget_config = {**getattr(provider, "_request_budget_config", {}), **{
        key: config[key] for key in ("input_token_limit", "output_token_limit", "context_window_tokens", "max_tokens") if key in config}}
    original = provider.generate
    def generate(_self, prompt, response_format=None, temperature=None, **kwargs):
        from .request_budget import check_provider_request
        from .work_budget import generation_defaults
        check_provider_request(_self, prompt, output_limit=kwargs.get("max_tokens", options.get("max_tokens")))
        effective = options.get("temperature", temperature)
        for key in ("max_tokens", "timeout"):
            if key in options and kwargs.get(key) is None:
                kwargs[key] = options[key]
        with generation_defaults(options):
            return original(prompt, response_format=response_format, temperature=effective, **kwargs)
    facade.generate = MethodType(generate, facade)
    return facade


# Both public names use the same isolated facade.
configure_phase_provider = phase_provider
