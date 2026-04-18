"""
VectorEngine LLM Provider

OpenAI-compatible relay API provider for multiple models.
Supports DeepSeek, GPT-4, Claude, and other models through VectorEngine.
"""

import logging
import time
from typing import Optional, Dict, Any, List

import httpx
from openai import OpenAI
from openai import APIConnectionError, APIError, APITimeoutError, RateLimitError

from src.config import settings
from .base import LLMProvider
from .config_loader import get_config_loader
from .errors import LLMConfigurationError, normalize_llm_transport_error
from .network_policy import build_network_policy


logger = logging.getLogger(__name__)


class VectorEngineProvider(LLMProvider):
    """VectorEngine API Provider (OpenAI-compatible)"""

    @staticmethod
    def _get_primary_provider_config():
        try:
            return get_config_loader().get_primary_provider_by_type("vectorengine")
        except Exception:
            return None

    @classmethod
    def _resolve_effective_network_policy(cls, requested_policy: Any | None) -> Any | None:
        provider = cls._get_primary_provider_config()
        if provider is None or provider.network is None:
            return requested_policy

        try:
            configured_policy = build_network_policy("vectorengine", provider.network)
        except ValueError as exc:
            raise LLMConfigurationError(str(exc)) from exc
        if requested_policy is None:
            return configured_policy

        requested_mode = str(getattr(requested_policy, "proxy_mode", "") or "").strip().lower()
        configured_mode = str(configured_policy.proxy_mode).strip().lower()
        if requested_mode and requested_mode != configured_mode:
            raise LLMConfigurationError(
                "VectorEngine network policy is enforced by YAML and cannot be overridden."
            )
        return configured_policy

    @classmethod
    def _resolve_default_runtime_settings(
        cls,
        model_selector: Optional[str],
    ) -> tuple[Optional[float], Optional[int]]:
        provider = cls._get_primary_provider_config()
        if provider is None:
            return None, None

        selected_model = None
        normalized_selector = (model_selector or "").strip().lower()
        for candidate in provider.models:
            candidate_alias = candidate.alias.strip().lower()
            candidate_real_model = candidate.real_model.strip().lower()
            if normalized_selector and (
                normalized_selector == candidate_alias
                or normalized_selector == candidate_real_model
            ):
                selected_model = candidate
                break

        if selected_model is None and provider.models:
            selected_model = sorted(provider.models, key=lambda item: item.priority)[0]

        model_timeout = None
        if selected_model is not None and isinstance(selected_model.config, dict):
            model_timeout = selected_model.config.get("timeout")

        return model_timeout, provider.retry_config.max_retries

    def _build_http_client(self) -> httpx.Client:
        policy = self.network_policy
        if policy is None:
            return httpx.Client(trust_env=False)

        client_kwargs: Dict[str, Any] = {
            "trust_env": bool(getattr(policy, "trust_env", False)),
        }
        if getattr(policy, "use_proxy", False):
            proxies = getattr(policy, "proxies", None) or {}
            proxy_url = proxies.get("https") or proxies.get("http")
            if proxy_url:
                client_kwargs["proxy"] = proxy_url

        return httpx.Client(**client_kwargs)

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        network_policy: Any | None = None,
    ):
        """
        Initialize VectorEngine Provider

        Args:
            api_key: VectorEngine API Key (defaults to VECTORENGINE_API_KEY env var)
            base_url: API base URL (defaults to https://api.vectorengine.ai/v1)
            model: Default model name (e.g., "deepseek-v3.2", "gpt-4o")
        """
        super().__init__()

        self.api_key = api_key or settings.vectorengine_api_key
        if not self.api_key:
            raise ValueError(
                "VectorEngine API key is required. Set VECTORENGINE_API_KEY environment variable, or pass api_key."
            )

        self.base_url = base_url or settings.vectorengine_base_url
        self.default_model = model or settings.vectorengine_default_model
        self.temperature = settings.vectorengine_temperature
        self.max_tokens = settings.vectorengine_max_tokens
        config_timeout, config_max_retries = self._resolve_default_runtime_settings(
            model or settings.vectorengine_default_model
        )
        self.timeout = (
            timeout if timeout is not None else (
                config_timeout if config_timeout is not None else settings.vectorengine_timeout
            )
        )
        self.max_retries = (
            max_retries if max_retries is not None else (
                config_max_retries if config_max_retries is not None else settings.vectorengine_max_retries
            )
        )
        self.network_policy = self._resolve_effective_network_policy(network_policy)

        # Initialize OpenAI client
        http_client = self._build_http_client()
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
            max_retries=self.max_retries,
            http_client=http_client,
        )

        logger.info(
            f"[VectorEngine] Initialized with base_url={self.base_url}, default_model={self.default_model}"
        )

    def generate(
        self,
        prompt: str,
        response_format: Optional[str] = None,
        temperature: Optional[float] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> str:
        """
        Generate text using VectorEngine API

        Args:
            prompt: Input prompt
            response_format: "json" for JSON output (optional)
            temperature: Sampling temperature (defaults to config)
            model: Model name override (defaults to default_model)
            **kwargs: Additional parameters

        Returns:
            Generated text
        """
        model_name = model or self.default_model
        temp = temperature if temperature is not None else self.temperature
        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        request_timeout = timeout if timeout is not None else self.timeout

        messages = [{"role": "user", "content": prompt}]

        # Build request parameters
        request_params = {
            "model": model_name,
            "messages": messages,
            "temperature": temp,
            "max_tokens": max_tokens,
            "timeout": request_timeout,
        }

        # Add response format if JSON requested
        if response_format == "json":
            request_params["response_format"] = {"type": "json_object"}

        try:
            logger.debug(f"[VectorEngine] Calling model={model_name}, temp={temp}")
            response = self.client.chat.completions.create(**request_params)

            content = response.choices[0].message.content

            logger.info(
                f"[VectorEngine] Success: model={model_name}, "
                f"tokens={response.usage.total_tokens} "
                f"(in={response.usage.prompt_tokens}, out={response.usage.completion_tokens})"
            )

            return content

        except RateLimitError as e:
            logger.error(f"[VectorEngine] Rate limit exceeded: {e}")
            normalized = normalize_llm_transport_error(e, provider_name="VectorEngine")
            raise normalized.error if normalized is not None else e
        except APITimeoutError as e:
            logger.error(f"[VectorEngine] Request timeout: {e}")
            normalized = normalize_llm_transport_error(e, provider_name="VectorEngine")
            raise normalized.error if normalized is not None else e
        except APIConnectionError as e:
            logger.error(f"[VectorEngine] Connection error: {e}")
            normalized = normalize_llm_transport_error(e, provider_name="VectorEngine")
            raise normalized.error if normalized is not None else e
        except APIError as e:
            logger.error(f"[VectorEngine] API error: {e}")
            normalized = normalize_llm_transport_error(e, provider_name="VectorEngine")
            raise normalized.error if normalized is not None else e
        except Exception as e:
            logger.error(f"[VectorEngine] Unexpected error: {e}")
            normalized = normalize_llm_transport_error(e, provider_name="VectorEngine")
            raise normalized.error if normalized is not None else e

    def translate(self, text: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Translate text (delegates to generate with translation prompt)"""
        context = context or {}

        # Build translation prompt
        glossary = context.get("glossary", {})
        style_guide = context.get("style_guide", "")

        glossary_text = "\n".join([f"- {k}: {v}" for k, v in glossary.items()]) if glossary else "无"

        prompt = f"""请将以下英文翻译成中文：

术语表：
{glossary_text}

风格指南：
{style_guide or "自然、专业"}

原文：
{text}

请直接输出中文译文，不要包含任何解释。"""

        return self.generate(prompt, temperature=0.3)

    def analyze(self, text: str) -> Dict[str, Any]:
        """Analyze text and extract terminology"""
        prompt = f"""分析以下文本，提取关键术语和建议的翻译风格。

文本：
{text}

请以 JSON 格式返回：
{{
  "terms": [{{"term": "...", "translation": "...", "context": "..."}}],
  "style_suggestions": ["..."]
}}"""

        response = self.generate(prompt, response_format="json", temperature=0.3)
        return self._parse_json_response(response)

    def check_consistency(
        self, paragraphs: List[Dict[str, str]], glossary: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Check translation consistency"""
        # Build paragraph pairs
        pairs_text = "\n\n".join([
            f"段落 {i+1}:\n原文: {p['source']}\n译文: {p['translation']}"
            for i, p in enumerate(paragraphs)
        ])

        glossary_text = "\n".join([f"- {k}: {v}" for k, v in glossary.items()])

        prompt = f"""检查以下译文的一致性问题：

术语表：
{glossary_text}

译文段落：
{pairs_text}

请以 JSON 格式返回问题列表：
{{
  "issues": [
    {{
      "paragraph_index": 0,
      "issue_type": "术语不一致",
      "description": "...",
      "suggestion": "..."
    }}
  ]
}}"""

        response = self.generate(prompt, response_format="json", temperature=0.3)
        result = self._parse_json_response(response)
        return result.get("issues", [])

    def translate_section(
        self,
        section_text: str,
        section_title: str,
        context: Dict[str, Any],
        paragraph_ids: List[str],
    ) -> List[Dict[str, str]]:
        """Translate one full section in batch mode and return paragraph-aligned results."""
        import json

        prompt = self._build_batch_translation_prompt(
            section_text, section_title, context, paragraph_ids
        )

        try:
            response = self.generate(prompt, response_format="json", temperature=0.5)
            result = self._parse_json_response(response)
        except Exception as exc:
            logger.error(f"[VectorEngine] Batch translation failed: {exc}")
            raise

        if isinstance(result, dict) and "translations" in result:
            return result["translations"]
        if isinstance(result, list):
            return result

        raise ValueError(
            "Batch translation response does not satisfy the JSON contract."
        )

    def _build_batch_translation_prompt(
        self,
        section_text: str,
        section_title: str,
        context: Dict[str, Any],
        paragraph_ids: List[str],
    ) -> str:
        """Build the batch translation prompt."""
        import json

        # Build glossary text
        glossary = context.get("glossary", [])
        if isinstance(glossary, list):
            glossary_text = "\n".join([
                f"- {term.get('original', '')} → {term.get('translation', '')}"
                for term in glossary if isinstance(term, dict)
            ])
        elif isinstance(glossary, dict):
            glossary_text = "\n".join([f"- {k} → {v}" for k, v in glossary.items()])
        else:
            glossary_text = "无"

        # Build guidelines
        guidelines = context.get("guidelines", [])
        guidelines_text = "\n".join([f"- {g}" for g in guidelines]) if guidelines else "无"

        # Build previous translations context
        prev_trans = context.get("previous_translations", [])
        if prev_trans:
            prev_lines = []
            for pair in prev_trans[-5:]:
                src_preview = pair.get("source", "")[:80]
                trans_preview = pair.get("translation", "")[:80]
                prev_lines.append(f"- EN: {src_preview}…\n  ZH: {trans_preview}…")
            previous_translations_block = "\n".join(prev_lines)
        else:
            previous_translations_block = "无"

        prompt = f"""# 章节批量翻译任务

## 章节信息
- 标题：{section_title}
- 文章主题：{context.get('article_theme', '')}
- 目标读者：{context.get('target_audience', '')}

## 术语表
{glossary_text}

## 翻译指南
{guidelines_text}

## 前文已确认译文（供参考）
{previous_translations_block}

## 待翻译章节内容
{section_text}

## 输出要求
请将上述章节内容翻译成中文，并按以下 JSON 格式返回：

{{
  "translations": [
    {{
      "id": "{paragraph_ids[0] if paragraph_ids else 'para_1'}",
      "translation": "第一段的中文翻译..."
    }},
    {{
      "id": "{paragraph_ids[1] if len(paragraph_ids) > 1 else 'para_2'}",
      "translation": "第二段的中文翻译..."
    }}
  ]
}}

注意：
1. 严格遵守术语表中的翻译
2. 保持专业、自然的中文表达
3. 段落 ID 必须与输入对应：{json.dumps(paragraph_ids)}
4. 返回的段落数量必须与输入段落数量一致
"""

        return prompt


    def _build_source_metadata_batch_prompt(
        self,
        entries: List[Dict[str, str]],
        context: Dict[str, Any],
    ) -> str:
        """Build the dedicated batch prompt for source/citation metadata."""
        import json

        glossary_block = str(context.get("glossary_block", "")).strip() or "(无命中术语)"
        entries_json = json.dumps(entries, ensure_ascii=False, indent=2)
        return self.prompt_manager.get(
            "longform/metadata/source_batch_translate",
            glossary_block=glossary_block,
            entry_count=len(entries),
            entries_json=entries_json,
        )

    def translate_source_metadata_batch(
        self,
        entries: List[Dict[str, str]],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, str]]:
        """Translate source/citation metadata entries in one JSON batch."""
        prompt = self._build_source_metadata_batch_prompt(entries, context or {})

        try:
            response = self.generate(prompt, response_format="json", temperature=0.2)
            result = self._parse_json_response(response)
        except Exception as exc:
            logger.error("[VectorEngine] Source metadata batch translation failed: %s", exc)
            raise

        if isinstance(result, dict) and "translations" in result:
            return result["translations"]
        if isinstance(result, list):
            return result

        raise ValueError(
            "Source metadata translation response does not satisfy the JSON contract."
        )

    def translate_title(
        self,
        title: str,
        context: Optional[Dict[str, Any]] = None,
        subtitle: Optional[str] = None,
    ) -> Dict[str, str]:
        """Translate article title and optional subtitle in one call."""
        context_lines: List[str] = []
        if context:
            if context.get("article_theme"):
                context_lines.append(f"- Article theme: {context['article_theme']}")
            if context.get("structure_summary"):
                context_lines.append(
                    f"- Structure summary: {context['structure_summary']}"
                )
            if context.get("target_audience"):
                context_lines.append(f"- Target audience: {context['target_audience']}")

        prompt = self.prompt_manager.get(
            "longform/auxiliary/title_translate",
            context_block="\n".join(context_lines) if context_lines else "- None",
            glossary_block=(context or {}).get("glossary_block", "(无命中术语)"),
            preservation_block=(
                (context or {}).get("preservation_block", "- 无额外保留项")
            ),
            title=title,
            subtitle=subtitle or "(无)",
        )
        raw = self.generate(prompt, temperature=0.3)

        result: Dict[str, str] = {}
        for line in raw.strip().splitlines():
            normalized = line.strip()
            if normalized.startswith("标题:") or normalized.startswith("标题："):
                result["title"] = normalized.split(":", 1)[-1].split("：", 1)[-1].strip()
            elif normalized.startswith("副标题:") or normalized.startswith("副标题："):
                value = normalized.split(":", 1)[-1].split("：", 1)[-1].strip()
                if value:
                    result["subtitle"] = value

        if not result.get("title"):
            result["title"] = raw.strip().splitlines()[0].strip()

        return result

    def translate_section_title(
        self,
        title: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Translate a section title with section-aware context."""
        context_lines: List[str] = []
        if context:
            if context.get("article_theme"):
                context_lines.append(f"- Article theme: {context['article_theme']}")
            if context.get("context"):
                context_lines.append(f"- Context: {context['context']}")
            if context.get("previous_section_title"):
                context_lines.append(
                    f"- Previous section: {context['previous_section_title']}"
                )
            if context.get("next_section_title"):
                context_lines.append(f"- Next section: {context['next_section_title']}")

        prompt = self.prompt_manager.get(
            "longform/auxiliary/section_title_translate",
            context_block="\n".join(context_lines) if context_lines else "- None",
            title=title,
        )
        return self.generate(prompt, temperature=0.3)


def create_vectorengine_provider(**kwargs) -> LLMProvider:
    """Factory function to create VectorEngine provider"""
    return VectorEngineProvider(**kwargs)
