"""
翻译系统限制和配置常量

集中管理系统中的各种限制值和配置常量。
"""

import os


class TranslationLimits:
    """翻译系统限制常量"""

    # 并发控制
    MAX_CONCURRENT_SECTIONS = int(os.getenv("MAX_CONCURRENT_SECTIONS", "10"))
    SECTION_LOCK_CACHE_SIZE = int(os.getenv("SECTION_LOCK_CACHE_SIZE", "256"))

    # 内容分块
    PRESCAN_SINGLE_CALL_LIMIT = 15000  # 单次预扫描调用的字符数上限
    PRESCAN_CHUNK_SIZE = 12000  # 预扫描分块大小
    MAX_PARAGRAPH_LENGTH = 800  # 默认段落最大长度

    # 文件操作
    FILE_WRITE_MAX_RETRIES = 3  # 文件写入最大重试次数
    FILE_WRITE_RETRY_DELAY_BASE = 0.1  # 文件写入重试延迟基数(秒)

    # 超时配置
    DEFAULT_LLM_TIMEOUT = 120  # 默认LLM调用超时(秒)
    DEFAULT_POST_TIMEOUT = 60  # 帖子翻译超时(秒)
    DEFAULT_TITLE_TIMEOUT = 30  # 标题生成超时(秒)

    # 上下文窗口
    DEFAULT_CONTEXT_WINDOW = 5  # 默认上下文窗口大小
    MAX_CONTEXT_TOKENS = 8192  # 最大上下文token数

    # 重试策略
    MAX_LLM_RETRIES = 5  # LLM调用最大重试次数
    LLM_RETRY_DELAY = 1.0  # LLM重试延迟(秒)

    # 批量操作
    MAX_BATCH_SIZE = 50  # 批量操作最大数量
    MAX_TITLE_BATCH_SIZE = 20  # 标题批量翻译最大数量

    @classmethod
    def validate(cls) -> None:
        """验证配置值的合理性"""
        if cls.MAX_CONCURRENT_SECTIONS < 1:
            raise ValueError("MAX_CONCURRENT_SECTIONS must be at least 1")
        if cls.PRESCAN_CHUNK_SIZE > cls.PRESCAN_SINGLE_CALL_LIMIT:
            raise ValueError("PRESCAN_CHUNK_SIZE cannot exceed PRESCAN_SINGLE_CALL_LIMIT")
        if cls.FILE_WRITE_MAX_RETRIES < 1:
            raise ValueError("FILE_WRITE_MAX_RETRIES must be at least 1")


# 在模块加载时验证配置
TranslationLimits.validate()
