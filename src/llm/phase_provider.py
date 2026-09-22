"""Bind phase options on a private facade; shared transports remain unchanged."""
from copy import copy
from types import MethodType


def configure_phase_provider(provider, settings):
    facade = copy(provider)
    runtime = {k: v for k, v in settings.items() if k in {"model", "temperature", "max_tokens", "timeout"}}
    facade._phase_config = runtime
    generate = provider.generate

    def phase_generate(_self, prompt, response_format=None, temperature=None, **kwargs):
        for key in ("max_tokens", "timeout"):
            if kwargs.get(key) is None and runtime.get(key) is not None:
                kwargs[key] = runtime[key]
        return generate(prompt, response_format=response_format,
                        temperature=runtime.get("temperature", temperature), **kwargs)

    facade.generate = MethodType(phase_generate, facade)
    return facade
