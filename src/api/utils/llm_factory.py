"""
LLM Factory - 统一的 LLM Provider 创建逻辑

避免代码重复，统一 API Key 管理。
支持最新 Google Gemini 模型。
"""

import os
import contextvars
import time
import logging
import requests
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Optional

from ...llm.gemini import GeminiProvider, create_gemini_provider


logger = logging.getLogger(__name__)


# ============ 支持的模型列表 ============
# Google Gemini 最先进的三个模型
ADVANCED_MODELS = {
    "gemini-3-pro": {
        "name": "Gemini 3 Pro",
        "description": "最强性能，适合复杂翻译任务",
        "max_tokens": 32768,
        "recommended_for": ["complex_translation", "academic_text", "professional_document"]
    },
    "gemini-3-pro-image": {
        "name": "Gemini 3 Pro Image",
        "description": "图像理解增强版，适合含图表的文档",
        "max_tokens": 32768,
        "recommended_for": ["multimodal_content", "scientific_paper", "presentation"]
    },
    "gemini-3-flash": {
        "name": "Gemini 3 Flash",
        "description": "快速响应版本，适合批量处理",
        "max_tokens": 8192,
        "recommended_for": ["batch_processing", "real_time_translation", "simple_content"]
    },
    # 保持向后兼容的原有模型
    "gemini-3-pro-preview": {
        "name": "Gemini 3 Pro Preview",
        "description": "预览版本，用于测试新功能",
        "max_tokens": 32768,
        "recommended_for": ["experimental_features", "testing"]
    }
}


def get_available_models() -> dict:
    """
    获取所有可用的模型列表

    Returns:
        dict: 模型信息字典
    """
    return ADVANCED_MODELS


def get_model_for_task(task_type: str) -> str:
    """
    根据任务类型推荐最佳模型

    Args:
        task_type: 任务类型

    Returns:
        str: 推荐的模型名称
    """
    task_model_map = {
        "complex_translation": "gemini-3-pro",
        "batch_processing": "gemini-3-flash",
        "multimodal_content": "gemini-3-pro-image",
        "real_time_translation": "gemini-3-flash",
        "academic_text": "gemini-3-pro",
        "professional_document": "gemini-3-pro"
    }

    return task_model_map.get(task_type, "gemini-3-pro")


# ============ Fallback Mode State ============
# 使用 contextvars 实现线程安全的状态管理
_backup_mode = contextvars.ContextVar('backup_mode', default=False)


def get_gemini_provider(model: str = "gemini-3-pro") -> GeminiProvider:
    """
    获取 Gemini Provider - 支持新的高级模型

    统一仅使用环境变量 GEMINI_BACKUP_API_KEY（付费 Key）

    Args:
        model: 模型名称，支持:
               - gemini-3-pro (默认，最强性能)
               - gemini-3-pro-image (图像理解增强)
               - gemini-3-flash (快速响应)
               - gemini-3-pro-preview (预览版)

    Returns:
        GeminiProvider: Gemini Provider 实例

    Raises:
        ValueError: 如果 API Key 未配置或模型不支持
    """
    # 验证模型名称
    if model not in ADVANCED_MODELS:
        supported_models = ", ".join(ADVANCED_MODELS.keys())
        raise ValueError(
            f"不支持的模型: {model}。支持的模型: {supported_models}"
        )

    backup_key = os.getenv("GEMINI_BACKUP_API_KEY")
    if not backup_key:
        raise ValueError(
            "GEMINI_BACKUP_API_KEY 环境变量未设置。请设置后重试：\n"
            "  Windows: set GEMINI_BACKUP_API_KEY=your_key\n"
            "  Linux/Mac: export GEMINI_BACKUP_API_KEY=your_key"
        )

    model_name = os.getenv("GEMINI_MODEL", model)
    model_type = "custom" if os.getenv("GEMINI_MODEL") else "reasoning"

    # 记录使用的模型信息
    model_info = ADVANCED_MODELS.get(model, {})
    logger.info(
        "[LLM Factory] 初始化 %s - %s",
        model_info.get("name", model),
        model_info.get("description", ""),
    )

    return create_gemini_provider(
        api_key=None, backup_api_key=backup_key, model=model_name, model_type=model_type
    )




# ============ Connectivity & Timeout Helpers ============

def _get_env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _should_check_connectivity() -> bool:
    return os.getenv("CONNECTIVITY_CHECK", "true").strip().lower() in {"1", "true", "yes", "y"}


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
    # If a proxy is configured, prefer REST which honors HTTP(S)_PROXY reliably.
    return _get_proxy_config() is not None


def _is_rate_limited(error_str: str) -> bool:
    return (
        "429" in error_str
        or "Too Many Requests" in error_str
        or "RESOURCE_EXHAUSTED" in error_str
        or "rate limit" in error_str.lower()
    )


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


def get_gemini_provider_backup_only(model: str = "gemini-3-pro-preview") -> GeminiProvider:
    """
    获取 Gemini Provider（仅使用备用 Key，不尝试主 Key）

    专用于全文翻译，直接使用备用 API Key，避免主 Key 配额限制。

    Args:
        model: 模型名称

    Returns:
        GeminiProvider: Gemini Provider 实例

    Raises:
        ValueError: 如果备用 API Key 未配置
    """
    backup_key = os.getenv("GEMINI_BACKUP_API_KEY")
    if not backup_key:
        raise ValueError(
            "GEMINI_BACKUP_API_KEY 环境变量未设置。请设置后重试：\n"
            "  Windows: set GEMINI_BACKUP_API_KEY=your_key\n"
            "  Linux/Mac: export GEMINI_BACKUP_API_KEY=your_key"
        )
    # 仅传入备用 key，不传主 key，这样会直接使用备用 key
    model_name = os.getenv("GEMINI_MODEL", model)
    model_type = "custom" if os.getenv("GEMINI_MODEL") else "reasoning"
    return create_gemini_provider(
        api_key=None, backup_api_key=backup_key, model=model_name, model_type=model_type
    )


def generate_with_fallback(
    prompt: str, primary_key: str = None, backup_key: str = None
) -> str:
    """
    智能生成策略：
    1. 默认使用主 Key
    2. 如果主 Key 失败，立即切换到备用 Key（不等待）
    3. 进入备用模式后，后续请求直接使用备用 Key，快速重试

    Args:
        prompt: 提示词
        primary_key: 主 API Key（可选，默认从环境变量获取）
        backup_key: 备用 API Key（可选）

    Returns:
        str: 生成的文本
    """
    try:
        from google import genai
    except Exception:
        genai = None

    # 仅使用备用付费 Key
    backup = backup_key or os.getenv("GEMINI_BACKUP_API_KEY")

    request_timeout = _get_env_int("GEMINI_TIMEOUT", 30)
    connectivity_timeout = _get_env_int("CONNECTIVITY_TIMEOUT", 5)
    _check_connectivity(timeout=connectivity_timeout)
    model_name = os.getenv("GEMINI_MODEL", "gemini-3-pro-preview")
    proxies = _get_proxy_config()
    use_rest = _use_rest_transport()

    start_time = time.monotonic()
    logger.info("[Gemini] generate_with_fallback start (len=%s)", len(prompt))

    if not backup:
        raise ValueError("未配置 GEMINI_BACKUP_API_KEY")

    # 使用 contextvars 获取当前上下文的备用模式状态
    use_backup = _backup_mode.get()

    # 强制使用备用 Key
    current_key = backup

    max_retries = 5  # 备用模式下增加重试次数

    for attempt in range(max_retries):
        try:
            if use_rest:
                response = _generate_with_rest(
                    prompt=prompt,
                    api_key=current_key,
                    model=model_name,
                    timeout=request_timeout,
                    proxies=proxies,
                )
            else:
                if genai is None:
                    raise RuntimeError("google-genai is not installed. Run: pip install google-genai")
                try:
                    client = genai.Client(api_key=current_key)
                except TypeError:
                    os.environ["GEMINI_API_KEY"] = current_key
                    client = genai.Client()
                response = _generate_with_timeout_fn(
                    lambda: client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                    ),
                    request_timeout,
                )
            duration = time.monotonic() - start_time
            logger.info("[Gemini] generate_with_fallback success in %.2fs", duration)
            return response if isinstance(response, str) else response.text
        except Exception as e:
            if isinstance(e, FutureTimeoutError):
                raise TimeoutError(f"Gemini request timed out after {request_timeout}s")
            error_str = str(e)

            # 如果已经在备用模式，快速重试
            if use_backup or current_key == backup:
                if attempt < max_retries - 1:
                    if _is_rate_limited(error_str):
                        retry_delay = min(2 ** attempt, 16)
                        logger.warning(
                            "[Gemini] 备用 Key 触发限流，等待 %.1fs 后重试 (%s/%s)...",
                            retry_delay,
                            attempt + 1,
                            max_retries,
                        )
                        time.sleep(retry_delay)
                    else:
                        logger.warning(
                            "[Gemini] 备用 Key 请求失败，快速重试 (%s/%s)...",
                            attempt + 1,
                            max_retries,
                        )
                        time.sleep(0.3)  # 极短等待
                    continue
                else:
                    logger.error("[Gemini] 备用 Key 重试 %s 次后仍然失败", max_retries)
                    raise

            # 最后一次尝试失败
            if attempt == max_retries - 1:
                duration = time.monotonic() - start_time
                logger.error("[Gemini] generate_with_fallback failed in %.2fs: %s", duration, e)
                raise
