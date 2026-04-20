"""LLM调用超时配置"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class TimeoutConfig:
    """统一的超时配置"""

    # 默认超时（秒）
    DEFAULT = 120

    # 按任务类型的超时配置
    LONG_ARTICLE = 300  # 长文翻译
    POST = 120          # 帖子翻译
    POST_OPTIMIZE = 120 # 帖子优化
    TITLE_GENERATE = 30 # 标题生成
    SLACK = 60          # Slack消息
    METADATA = 60       # 元数据生成
    ANALYSIS = 180      # 分析任务

    @classmethod
    def get_timeout(cls, task_type: Optional[str] = None) -> int:
        """根据任务类型获取超时时间"""
        if not task_type:
            return cls.DEFAULT

        timeout_map = {
            "long_article": cls.LONG_ARTICLE,
            "post": cls.POST,
            "post_optimize": cls.POST_OPTIMIZE,
            "title_generate": cls.TITLE_GENERATE,
            "slack": cls.SLACK,
            "metadata": cls.METADATA,
            "analysis": cls.ANALYSIS,
        }

        return timeout_map.get(task_type, cls.DEFAULT)
