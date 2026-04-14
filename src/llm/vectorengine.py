"""
VectorEngine LLM Provider

OpenAI-compatible relay API provider for multiple models.
Supports DeepSeek, GPT-4, Claude, and other models through VectorEngine.
"""

import logging
import time
from typing import Optional, Dict, Any, List

from openai import OpenAI
from openai import APIError, APITimeoutError, RateLimitError

from src.config import settings
from .base import LLMProvider


logger = logging.getLogger(__name__)


class VectorEngineProvider(LLMProvider):
    """VectorEngine API Provider (OpenAI-compatible)"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
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
        self.timeout = settings.vectorengine_timeout
        self.max_retries = settings.vectorengine_max_retries

        # Initialize OpenAI client
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
            max_retries=self.max_retries,
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

        messages = [{"role": "user", "content": prompt}]

        # Build request parameters
        request_params = {
            "model": model_name,
            "messages": messages,
            "temperature": temp,
            "max_tokens": max_tokens,
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
            raise
        except APITimeoutError as e:
            logger.error(f"[VectorEngine] Request timeout: {e}")
            raise
        except APIError as e:
            logger.error(f"[VectorEngine] API error: {e}")
            raise
        except Exception as e:
            logger.error(f"[VectorEngine] Unexpected error: {e}")
            raise

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


def create_vectorengine_provider(**kwargs) -> LLMProvider:
    """Factory function to create VectorEngine provider"""
    return VectorEngineProvider(**kwargs)
