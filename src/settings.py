"""
Application settings.

Centralized configuration loaded from environment variables and `.env`.
"""

from __future__ import annotations

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    app_name: str = "Translation Agent"
    app_version: str = "1.0.0"
    debug: bool = False

    # LLM
    llm_provider: str = "gemini"
    llm_default_model: str = "pro-official"  # Default model alias for all tasks

    # Task-specific default models (can override llm_default_model)
    llm_model_longform: str = "deepseek-v3.2"  # Long-form translation
    llm_model_post: str = "flash-official"      # Post translation
    llm_model_analysis: str = "pro-official"    # Text analysis
    llm_model_title: str = "flash-official"     # Title translation
    llm_model_metadata: str = "flash-official"  # Metadata translation

    # Server
    api_host: str = "127.0.0.1"
    api_port: int = 54321
    api_reload: bool = False

    # CORS
    cors_origins: list[str] = ["*"]
    cors_credentials: bool = True
    cors_methods: list[str] = ["*"]
    cors_headers: list[str] = ["*"]

    # Gemini
    gemini_api_key: str = ""
    gemini_backup_api_key: str = ""  # legacy compatibility
    gemini_flash_model: str = "gemini-flash-latest"
    gemini_pro_model: str = "gemini-3-pro-preview"
    gemini_preview_model: str = "gemini-3.1-pro-preview"
    gemini_model: str = "pro"  # selector/alias: flash/pro/preview or concrete model id
    gemini_backup_model: str = "flash"  # selector/alias or concrete model id
    gemini_temperature: float = 0.7
    gemini_max_tokens: int = 8192
    gemini_max_retries: int = 5
    gemini_retry_count: int = 3
    gemini_retry_delay: float = 1.0
    gemini_timeout: int = 120
    gemini_http_proxy: Optional[str] = None
    gemini_https_proxy: Optional[str] = None
    gemini_no_proxy: Optional[str] = None

    # VectorEngine (OpenAI-compatible relay)
    vectorengine_api_key: str = ""
    vectorengine_base_url: str = "https://api.vectorengine.ai/v1"
    vectorengine_default_model: str = "deepseek-v3.2"
    vectorengine_temperature: float = 0.7
    vectorengine_max_tokens: int = 8192
    vectorengine_timeout: int = 600
    vectorengine_max_retries: int = 3

    # Storage
    projects_path: str = "projects"
    glossary_path: str = "glossary"

    # Translation
    default_context_window: int = 5
    default_translation_style: str = "natural_professional"
    default_segment_level: str = "h2"
    translation_prompt_style: str = "original"

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    log_file: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def get_llm_config(self, provider: str = "gemini") -> dict:
        resolved_provider = (provider or self.llm_provider).strip().lower()
        if resolved_provider == "gemini":
            api_keys = [
                key
                for key in [self.gemini_api_key, self.gemini_backup_api_key]
                if key
            ]
            return {
                "api_key": self.gemini_api_key,
                "backup_api_key": self.gemini_backup_api_key,
                "api_keys": api_keys,
                "flash_model": self.gemini_flash_model,
                "pro_model": self.gemini_pro_model,
                "preview_model": self.gemini_preview_model,
                "model": self.gemini_model,
                "backup_model": self.gemini_backup_model,
                "temperature": self.gemini_temperature,
                "max_tokens": self.gemini_max_tokens,
                "max_retries": self.gemini_max_retries,
                "retry_count": self.gemini_retry_count,
                "retry_delay": self.gemini_retry_delay,
                "timeout": self.gemini_timeout,
            }
        elif resolved_provider == "vectorengine":
            return {
                "api_key": self.vectorengine_api_key,
                "base_url": self.vectorengine_base_url,
                "default_model": self.vectorengine_default_model,
                "temperature": self.vectorengine_temperature,
                "max_tokens": self.vectorengine_max_tokens,
                "timeout": self.vectorengine_timeout,
                "max_retries": self.vectorengine_max_retries,
            }
        raise ValueError(f"Unsupported LLM provider: {resolved_provider}")

    def validate_required_settings(self):
        errors = []

        provider = self.llm_provider.strip().lower()
        if provider == "gemini":
            if not (self.gemini_api_key or self.gemini_backup_api_key):
                errors.append(
                    "Gemini requires GEMINI_API_KEY or GEMINI_BACKUP_API_KEY in .env."
                )
        elif provider == "vectorengine":
            if not self.vectorengine_api_key:
                errors.append(
                    "VectorEngine requires VECTORENGINE_API_KEY in .env."
                )

        if errors:
            raise ValueError("\n".join(errors))

    @property
    def is_production(self) -> bool:
        return not self.debug


settings = Settings()
