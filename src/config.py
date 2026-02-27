"""
Translation Agent - 统一配置管理

使用 Pydantic Settings 管理所有配置项，支持环境变量和 .env 文件。
"""

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    # ============ 应用配置 ============
    app_name: str = "Translation Agent"
    app_version: str = "1.0.0"
    debug: bool = False

    # ============ 服务器配置 ============
    api_host: str = "127.0.0.1"
    api_port: int = 54321
    api_reload: bool = False  # 开发模式下自动重载

    # ============ CORS 配置 ============
    cors_origins: list[str] = ["*"]
    cors_credentials: bool = True
    cors_methods: list[str] = ["*"]
    cors_headers: list[str] = ["*"]

    # ============ LLM 配置 ============
    # Gemini
    gemini_api_key: str = ""  # 必须通过环境变量设置
    gemini_backup_api_key: str = ""  # 备用付费 Key（当前默认使用）
    gemini_model: str = "gemini-1.5-pro"
    gemini_temperature: float = 0.7
    gemini_max_tokens: int = 8192
    gemini_retry_count: int = 3
    gemini_retry_delay: float = 1.0
    gemini_timeout: int = 60  # 超时时间（秒）

    # OpenAI（预留，暂未实现）
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4"

    # ============ 存储配置 ============
    projects_path: str = "projects"
    conversations_path: str = "conversations"
    glossary_path: str = "glossary"

    # ============ 翻译配置 ============
    default_context_window: int = 5  # 上下文窗口大小
    default_translation_style: str = "natural_professional"
    default_segment_level: str = "h2"  # 章节分割级别

    # ============ 缓存配置 ============
    cache_enabled: bool = False
    cache_backend: str = "memory"  # memory/redis/file
    cache_ttl: int = 86400  # 缓存有效期（秒，默认 1 天）
    redis_url: Optional[str] = None  # 如果使用 Redis

    # ============ 限流配置 ============
    rate_limit_enabled: bool = False
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 1000

    # ============ 日志配置 ============
    log_level: str = "INFO"  # DEBUG/INFO/WARNING/ERROR
    log_format: str = "json"  # json/text
    log_file: Optional[str] = None  # 日志文件路径，None 表示仅输出到控制台

    # ============ 数据库配置（预留） ============
    database_url: Optional[str] = None
    database_pool_size: int = 5
    database_max_overflow: int = 10

    # ============ 认证配置（预留） ============
    jwt_secret_key: Optional[str] = None
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 小时

    # ============ 监控配置 ============
    sentry_dsn: Optional[str] = None  # Sentry 错误监控
    enable_metrics: bool = False  # 是否启用指标收集

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # 忽略未定义的环境变量
    )

    def get_llm_config(self, provider: str = "gemini") -> dict:
        """获取 LLM 配置"""
        if provider == "gemini":
            return {
                "api_key": self.gemini_backup_api_key or self.gemini_api_key,
                "model": self.gemini_model,
                "temperature": self.gemini_temperature,
                "max_tokens": self.gemini_max_tokens,
                "retry_count": self.gemini_retry_count,
                "retry_delay": self.gemini_retry_delay,
                "timeout": self.gemini_timeout,
            }
        if provider == "openai":
            return {
                "api_key": self.openai_api_key,
                "model": self.openai_model,
            }
        raise ValueError(f"Unsupported LLM provider: {provider}")

    def validate_required_settings(self):
        """验证必需的配置项"""
        errors = []

        if not self.gemini_backup_api_key:
            errors.append("GEMINI_BACKUP_API_KEY 未设置，请在 .env 文件中配置")

        if self.cache_enabled and self.cache_backend == "redis" and not self.redis_url:
            errors.append("启用 Redis 缓存时必须设置 REDIS_URL")

        if errors:
            raise ValueError("\n".join(errors))

    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return not self.debug


# 全局配置实例
settings = Settings()

# 启动时验证配置
try:
    settings.validate_required_settings()
except ValueError as e:
    print(f"配置验证失败:\n{e}")
    print("\n提示: 请确认 .env 文件中配置了所有必需的环境变量")
