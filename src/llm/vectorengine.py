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

from src.settings import settings
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
        }

        # Add response format if JSON requested
        if response_format == "json":
            request_params["response_format"] = {"type": "json_object"}

        try:
            logger.info(f"[VectorEngine] Calling model={model_name}, temp={temp}, timeout={request_timeout}")
            client = self.client
            if hasattr(self.client, "with_options"):
                client = self.client.with_options(
                    timeout=request_timeout,
                    max_retries=(0 if timeout is not None else self.max_retries),
                )
            response = client.chat.completions.create(**request_params)

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

    def translate(self, text: str, context: Optional[Dict[str, Any]] = None, timeout: Optional[float] = None) -> str:
        """Translate text using the shared prompt builder"""
        context_data = dict(context or {})
        prompt = self._build_translation_prompt(text, context_data)
        return self.generate(prompt, temperature=0.5, timeout=timeout)

    def _build_translation_prompt(self, text: str, context: Dict[str, Any]) -> str:
        """Build the paragraph translation prompt via the shared prompt builder."""
        from ..prompts.prompt_builder import get_prompt_builder

        builder = get_prompt_builder(style="longform")

        # Extract runtime context for the paragraph prompt builder.
        glossary = context.get("glossary", [])
        previous_paragraphs = context.get("previous_paragraphs", [])
        next_preview = context.get("next_preview", [])
        article_title = context.get("article_title")
        current_section_title = context.get("current_section_title")
        heading_chain = context.get("heading_chain")
        style_guide = context.get("style_guide")
        learned_rules = context.get("learned_rules")
        instruction = context.get("instruction")
        format_tokens = context.get("format_tokens", [])
        term_usage = context.get("term_usage")

        # Delegate prompt assembly to the long-form prompt builder.
        prompt = builder.build_prompt(
            source_text=text,
            glossary=glossary,
            previous_paragraphs=previous_paragraphs,
            next_preview=next_preview,
            article_title=article_title,
            current_section_title=current_section_title,
            heading_chain=heading_chain,
            style_guide=style_guide,
            learned_rules=learned_rules,
            instruction=instruction,
            format_tokens=format_tokens,
            term_usage=term_usage,
        )

        return prompt

    def deep_analyze_with_term_verification(
        self,
        outline: str,
        sampled_text: str,
        high_freq_candidates: List[Dict[str, Any]],
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        合并深度分析和术语验证（方案6）

        Args:
            outline: 文档大纲
            sampled_text: 采样文本
            high_freq_candidates: 高频术语候选列表
            timeout: 超时时间（秒）

        Returns:
            Dict: 合并分析结果
        """
        # 构建高频术语列表文本
        high_freq_terms_list = "\n".join([
            f"{i+1}. **{term['term']}** (出现 {term['frequency']} 次)"
            for i, term in enumerate(high_freq_candidates)
        ])

        # 使用prompt_manager构建prompt
        prompt = self.prompt_manager.get(
            "longform/analysis/deep_analyze_with_terms",
            outline=outline,
            sampled_text=sampled_text,
            high_freq_terms_list=high_freq_terms_list
        )

        # 调用LLM
        response = self.generate(
            prompt,
            response_format="json",
            temperature=0.3,
            timeout=timeout
        )

        # 清理响应：移除markdown代码块标记
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]  # 移除 ```json
        elif response.startswith("```"):
            response = response[3:]  # 移除 ```
        if response.endswith("```"):
            response = response[:-3]  # 移除结尾的 ```
        response = response.strip()

        # 解析JSON响应
        import json
        import re
        try:
            result = json.loads(response)
            return result
        except json.JSONDecodeError as e:
            # 尝试修复常见的JSON错误
            logger.warning(f"[VectorEngine] Initial JSON parse failed: {e}, attempting to fix...")

            # 尝试1: 截断到最后一个完整的对象
            try:
                # 找到最后一个完整的 }
                last_brace = response.rfind('}')
                if last_brace > 0:
                    fixed_response = response[:last_brace + 1]
                    result = json.loads(fixed_response)
                    logger.info(f"[VectorEngine] Successfully parsed truncated JSON (method 1)")
                    return result
            except:
                pass

            # 尝试2: 智能补全未闭合的字符串和对象
            try:
                fixed = response
                # 移除未闭合的字符串（找到最后一个完整的引号对）
                quote_count = fixed.count('"')
                if quote_count % 2 != 0:
                    # 奇数个引号，移除最后一个未闭合的字符串
                    last_quote = fixed.rfind('"')
                    if last_quote > 0:
                        # 回退到上一个逗号或换行
                        prev_comma = fixed.rfind(',', 0, last_quote)
                        prev_newline = fixed.rfind('\n', 0, last_quote)
                        cutoff = max(prev_comma, prev_newline)
                        if cutoff > 0:
                            fixed = fixed[:cutoff]

                # 补全缺失的括号
                open_braces = fixed.count('{')
                close_braces = fixed.count('}')
                if open_braces > close_braces:
                    fixed += '\n}' * (open_braces - close_braces)

                open_brackets = fixed.count('[')
                close_brackets = fixed.count(']')
                if open_brackets > close_brackets:
                    fixed += ']' * (open_brackets - close_brackets)

                result = json.loads(fixed)
                logger.info(f"[VectorEngine] Successfully parsed with smart completion (method 2)")
                return result
            except:
                pass

            # 尝试3: 逐行回退找到可解析的部分
            try:
                lines = response.split('\n')
                for i in range(len(lines) - 1, max(0, len(lines) - 50), -1):
                    partial = '\n'.join(lines[:i])

                    # 移除未闭合的字符串
                    if partial.count('"') % 2 != 0:
                        last_quote = partial.rfind('"')
                        if last_quote > 0:
                            prev_comma = partial.rfind(',', 0, last_quote)
                            if prev_comma > 0:
                                partial = partial[:prev_comma]

                    # 补全括号
                    if partial.count('{') > partial.count('}'):
                        partial += '\n}' * (partial.count('{') - partial.count('}'))
                    if partial.count('[') > partial.count(']'):
                        partial += ']' * (partial.count('[') - partial.count(']'))

                    try:
                        result = json.loads(partial)
                        logger.info(f"[VectorEngine] Successfully parsed partial JSON (method 3: kept {i}/{len(lines)} lines)")
                        return result
                    except:
                        continue
            except:
                pass

            # 尝试4: 提取关键字段（最后的手段）
            try:
                # 尝试提取至少包含theme和key_arguments的部分
                result = {}

                # 提取theme
                theme_match = re.search(r'"theme"\s*:\s*"([^"]*)"', response)
                if theme_match:
                    result['theme'] = theme_match.group(1)

                # 提取key_arguments
                key_args_match = re.search(r'"key_arguments"\s*:\s*\[(.*?)\]', response, re.DOTALL)
                if key_args_match:
                    args_text = key_args_match.group(1)
                    args = re.findall(r'"([^"]*)"', args_text)
                    result['key_arguments'] = args

                # 提取structure_summary
                struct_match = re.search(r'"structure_summary"\s*:\s*"([^"]*)"', response)
                if struct_match:
                    result['structure_summary'] = struct_match.group(1)

                # 提取style
                style_match = re.search(r'"style"\s*:\s*\{([^}]*)\}', response)
                if style_match:
                    style_text = style_match.group(1)
                    style = {}
                    for field in ['tone', 'target_audience', 'translation_voice']:
                        field_match = re.search(f'"{field}"\s*:\s*"([^"]*)"', style_text)
                        if field_match:
                            style[field] = field_match.group(1)
                    result['style'] = style

                if result:
                    logger.warning(f"[VectorEngine] Extracted partial data using regex (method 4): {list(result.keys())}")
                    # 补充默认值
                    result.setdefault('sampled_terms', [])
                    result.setdefault('verified_high_freq_terms', [])
                    result.setdefault('challenges', [])
                    result.setdefault('guidelines', [])
                    return result
            except:
                pass

            # 所有修复尝试都失败
            logger.error(f"[VectorEngine] Failed to parse JSON response: {e}")
            logger.error(f"[VectorEngine] Response length: {len(response)}")
            logger.error(f"[VectorEngine] Response preview: {response[:500]}")
            logger.error(f"[VectorEngine] Response ending: {response[-500:]}")
            raise ValueError(f"Invalid JSON response from LLM: {e}")

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

    def deep_analyze_document(
        self,
        outline: str,
        sampled_text: str,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        深度分析文档（不包含术语验证）

        Args:
            outline: 文档大纲
            sampled_text: 采样文本
            timeout: 超时时间（秒）

        Returns:
            Dict: 分析结果
        """
        # 使用prompt_manager构建prompt
        prompt = self.prompt_manager.get(
            "longform/analysis/deep_analyze",
            outline=outline,
            sampled_text=sampled_text
        )

        # 调用LLM
        response = self.generate(
            prompt,
            response_format="json",
            temperature=0.3,
            timeout=timeout
        )

        # 清理和解析响应
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        elif response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()

        import json
        result = json.loads(response)
        return result

    def verify_high_frequency_terms(
        self,
        sampled_text: str,
        high_freq_candidates: List[Dict[str, Any]],
        timeout: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        验证高频术语候选

        Args:
            sampled_text: 采样文本
            high_freq_candidates: 高频术语候选列表
            timeout: 超时时间（秒）

        Returns:
            List[Dict]: 验证通过的术语列表
        """
        # 构建高频术语列表文本
        high_freq_terms_list = "\n".join([
            f"{i+1}. **{term['term']}** (出现 {term['frequency']} 次)"
            for i, term in enumerate(high_freq_candidates)
        ])

        # 使用prompt_manager构建prompt
        prompt = self.prompt_manager.get(
            "longform/analysis/verify_terms",
            sampled_text=sampled_text,
            high_freq_terms_list=high_freq_terms_list
        )

        # 调用LLM
        response = self.generate(
            prompt,
            response_format="json",
            temperature=0.3,
            timeout=timeout
        )

        # 清理和解析响应
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        elif response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()

        import json
        result = json.loads(response)
        return result.get("verified_terms", [])

    def check_consistency(
        self, paragraphs: List[Dict[str, str]], glossary: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Check translation consistency"""
        # Build paragraph pairs
        pairs_text = "\n\n".join([
            f"段落 {i+1}:\n原文: {p['source']}\n译文: {p['translation']}"
            for i, p in enumerate(paragraphs)
        ])

        # Handle both list and dict formats
        if isinstance(glossary, list):
            glossary_text = "\n".join([
                f"- {term.get('original', '')}: {term.get('translation', '')}"
                for term in glossary if isinstance(term, dict)
            ])
        elif isinstance(glossary, dict):
            glossary_text = "\n".join([f"- {k}: {v}" for k, v in glossary.items()])
        else:
            glossary_text = "无"

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
            response = self.generate(prompt, response_format="json", temperature=0.3)
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
