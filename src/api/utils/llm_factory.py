"""
LLM Factory

Centralized Gemini provider creation and fallback generation helpers.
"""

from __future__ import annotations

import contextvars
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Optional

import requests

from ...llm.gemini import GeminiProvider, create_gemini_provider


logger = logging.getLogger(__name__)


# Keep compatibility with existing feature flags that may use this context var.
_backup_mode = contextvars.ContextVar("backup_mode", default=False)


ADVANCED_MODELS = {
    "gemini-3-pro": {
        "name": "Gemini 3 Pro",
        "description": "High quality model for complex translation tasks",
        "max_tokens": 32768,
        "recommended_for": [
            "complex_translation",
            "academic_text",
            "professional_document",
        ],
    },
    "gemini-3-pro-image": {
        "name": "Gemini 3 Pro Image",
        "description": "Enhanced multimodal reasoning for image-heavy documents",
        "max_tokens": 32768,
        "recommended_for": [
            "multimodal_content",
            "scientific_paper",
            "presentation",
        ],
    },
    "gemini-3-flash": {
        "name": "Gemini 3 Flash",
        "description": "Fast model for throughput-oriented tasks",
        "max_tokens": 8192,
        "recommended_for": [
            "batch_processing",
            "real_time_translation",
            "simple_content",
        ],
    },
    "gemini-3-pro-preview": {
        "name": "Gemini 3 Pro Preview",
        "description": "Preview model for compatibility with existing deployments",
        "max_tokens": 32768,
        "recommended_for": ["experimental_features", "testing"],
    },
}


def get_available_models() -> dict:
    return ADVANCED_MODELS


def get_model_for_task(task_type: str) -> str:
    task_model_map = {
        "complex_translation": "gemini-3-pro",
        "batch_processing": "gemini-3-flash",
        "multimodal_content": "gemini-3-pro-image",
        "real_time_translation": "gemini-3-flash",
        "academic_text": "gemini-3-pro",
        "professional_document": "gemini-3-pro",
    }
    return task_model_map.get(task_type, "gemini-3-pro")


def _get_gemini_api_key_from_env() -> str | None:
    """
    Preferred key name is GEMINI_API_KEY.
    Keep GEMINI_BACKUP_API_KEY as compatibility fallback.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        return api_key

    legacy_key = os.getenv("GEMINI_BACKUP_API_KEY")
    if legacy_key:
        logger.warning(
            "[Gemini] GEMINI_BACKUP_API_KEY is deprecated. Please migrate to GEMINI_API_KEY."
        )
    return legacy_key


def _get_env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _should_check_connectivity() -> bool:
    return os.getenv("CONNECTIVITY_CHECK", "true").strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
    }


def _get_proxy_config() -> dict | None:
    http_proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
    https_proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
    if http_proxy or https_proxy:
        return {
            "http": http_proxy,
            "https": https_proxy or http_proxy,
        }
    return None


def _use_rest_transport() -> bool:
    override = os.getenv("GEMINI_USE_REST")
    if override is not None:
        return override.strip().lower() in {"1", "true", "yes", "y"}
    # REST route respects proxy env vars more reliably.
    return _get_proxy_config() is not None


def _is_rate_limited(error_str: str) -> bool:
    return (
        "429" in error_str
        or "Too Many Requests" in error_str
        or "RESOURCE_EXHAUSTED" in error_str
        or "rate limit" in error_str.lower()
    )


def _is_high_demand_unavailable(error_str: str) -> bool:
    text = error_str.lower()
    return (
        "currently experiencing high demand" in text
        or ('"status": "unavailable"' in text and "high demand" in text)
        or "status\":\"unavailable" in text
    )


def _error_to_text(exc: Exception) -> str:
    text = str(exc)
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        try:
            data = exc.response.json()
            err = data.get("error", {}) if isinstance(data, dict) else {}
            message = err.get("message")
            status = err.get("status")
            if message:
                text = f"{text} | {message}"
            if status:
                text = f"{text} | status={status}"
        except Exception:
            body = (exc.response.text or "").strip()
            if body:
                text = f"{text} | body={body[:300]}"
    return text


def _generate_with_rest(
    prompt: str,
    api_key: str,
    model: str,
    timeout: int | None,
    proxies: dict | None,
    temperature: float = 0.7,
) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature},
    }
    headers = {"x-goog-api-key": api_key}
    response = requests.post(
        url,
        json=payload,
        headers=headers,
        timeout=timeout if timeout and timeout > 0 else None,
        proxies=proxies,
    )
    response.raise_for_status()
    data = response.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as exc:
        raise RuntimeError(f"Unexpected Gemini REST response: {data}") from exc


def _check_connectivity(timeout: int = 5) -> None:
    if not _should_check_connectivity():
        return
    proxies = _get_proxy_config()
    try:
        requests.get(
            "https://generativelanguage.googleapis.com/",
            timeout=timeout,
            proxies=proxies,
        )
    except Exception as exc:
        proxy_hint = ""
        if not proxies:
            proxy_hint = " Consider setting HTTP_PROXY/HTTPS_PROXY if you are behind a proxy."
        raise ConnectionError(f"Cannot reach Gemini API.{proxy_hint} {exc}")


def _generate_with_timeout_fn(fn, timeout: int | None):
    if not timeout or timeout <= 0:
        return fn()
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(fn)
    try:
        return future.result(timeout=timeout)
    except FutureTimeoutError:
        future.cancel()
        raise
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def get_gemini_provider(model: str = "gemini-3-pro") -> GeminiProvider:
    if model not in ADVANCED_MODELS:
        supported_models = ", ".join(ADVANCED_MODELS.keys())
        raise ValueError(
            f"Unsupported model: {model}. Supported models: {supported_models}"
        )

    api_key = _get_gemini_api_key_from_env()
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is not set. Please configure it first:\n"
            "  Windows: set GEMINI_API_KEY=your_key\n"
            "  Linux/Mac: export GEMINI_API_KEY=your_key"
        )

    model_name = os.getenv("GEMINI_MODEL", model)
    model_type = "custom" if os.getenv("GEMINI_MODEL") else "reasoning"
    model_info = ADVANCED_MODELS.get(model, {})
    logger.info(
        "[LLM Factory] init model=%s (%s)",
        model_info.get("name", model),
        model_info.get("description", ""),
    )

    return create_gemini_provider(
        api_key=None,
        backup_api_key=api_key,
        model=model_name,
        model_type=model_type,
    )


def get_gemini_provider_backup_only(
    model: str = "gemini-3-pro-preview",
) -> GeminiProvider:
    """
    Kept for compatibility. It now uses the same GEMINI_API_KEY source.
    """
    api_key = _get_gemini_api_key_from_env()
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is not set. Please configure it first:\n"
            "  Windows: set GEMINI_API_KEY=your_key\n"
            "  Linux/Mac: export GEMINI_API_KEY=your_key"
        )
    model_name = os.getenv("GEMINI_MODEL", model)
    model_type = "custom" if os.getenv("GEMINI_MODEL") else "reasoning"
    return create_gemini_provider(
        api_key=None,
        backup_api_key=api_key,
        model=model_name,
        model_type=model_type,
    )


def generate_with_fallback(
    prompt: str, primary_key: str = None, backup_key: str = None
) -> str:
    try:
        from google import genai
    except Exception:
        genai = None

    api_key = primary_key or backup_key or _get_gemini_api_key_from_env()
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured")

    request_timeout = _get_env_int("GEMINI_TIMEOUT", 30)
    connectivity_timeout = _get_env_int("CONNECTIVITY_TIMEOUT", 5)
    _check_connectivity(timeout=connectivity_timeout)

    primary_model = os.getenv("GEMINI_MODEL", "gemini-3-pro-preview")
    backup_model = os.getenv("GEMINI_BACKUP_MODEL", "gemini-flash-latest").strip() or None
    proxies = _get_proxy_config()
    use_rest = _use_rest_transport()

    max_retries = 5
    current_model = primary_model
    switched_to_backup_model = False
    start_time = time.monotonic()

    logger.info(
        "[Gemini] generate start len=%s model=%s backup_model=%s timeout=%ss transport=%s",
        len(prompt),
        primary_model,
        backup_model or "-",
        request_timeout,
        "rest" if use_rest else "sdk",
    )

    for attempt in range(max_retries):
        try:
            if use_rest:
                response = _generate_with_rest(
                    prompt=prompt,
                    api_key=api_key,
                    model=current_model,
                    timeout=request_timeout,
                    proxies=proxies,
                )
            else:
                if genai is None:
                    raise RuntimeError(
                        "google-genai is not installed. Run: pip install google-genai"
                    )
                try:
                    client = genai.Client(api_key=api_key)
                except TypeError:
                    os.environ["GEMINI_API_KEY"] = api_key
                    client = genai.Client()

                response = _generate_with_timeout_fn(
                    lambda: client.models.generate_content(
                        model=current_model,
                        contents=prompt,
                    ),
                    request_timeout,
                )

            duration = time.monotonic() - start_time
            logger.info(
                "[Gemini] generate success in %.2fs (model=%s attempt=%s/%s)",
                duration,
                current_model,
                attempt + 1,
                max_retries,
            )
            return response if isinstance(response, str) else response.text
        except Exception as exc:
            if isinstance(exc, FutureTimeoutError):
                raise TimeoutError(f"Gemini request timed out after {request_timeout}s")

            error_text = _error_to_text(exc)

            if (
                backup_model
                and not switched_to_backup_model
                and current_model != backup_model
                and _is_high_demand_unavailable(error_text)
                and attempt < max_retries - 1
            ):
                switched_to_backup_model = True
                current_model = backup_model
                logger.warning(
                    "[Gemini] model '%s' is overloaded; switch to backup model '%s' and retry (%s/%s).",
                    primary_model,
                    backup_model,
                    attempt + 1,
                    max_retries,
                )
                continue

            if attempt < max_retries - 1:
                if _is_rate_limited(error_text):
                    retry_delay = min(2**attempt, 16)
                    logger.warning(
                        "[Gemini] rate limited on model '%s'; retry in %.1fs (%s/%s). err=%s",
                        current_model,
                        retry_delay,
                        attempt + 1,
                        max_retries,
                        error_text,
                    )
                    time.sleep(retry_delay)
                else:
                    logger.warning(
                        "[Gemini] request failed on model '%s'; quick retry (%s/%s). err=%s",
                        current_model,
                        attempt + 1,
                        max_retries,
                        error_text,
                    )
                    time.sleep(0.3)
                continue

            duration = time.monotonic() - start_time
            logger.error(
                "[Gemini] generate failed in %.2fs after %s attempts (model=%s). err=%s",
                duration,
                max_retries,
                current_model,
                error_text,
            )
            raise

