"""
项目常量定义

集中管理项目中使用的各种常量，避免硬编码魔法数字。
"""

# ============ 文本长度限制 ============
MAX_ANALYSIS_LENGTH = 8000  # 项目分析时的最大文本长度
MAX_SECTION_ANALYSIS_LENGTH = 5000  # 章节分析时的最大文本长度
MAX_DEEP_ANALYSIS_LENGTH = 15000  # 深度分析时的最大文本长度

# ============ 上下文窗口 ============
DEFAULT_CONTEXT_WINDOW_SIZE = 5  # 默认上下文窗口大小
MAX_PREVIOUS_PARAGRAPHS = 5  # 最大前文段落数
MAX_NEXT_PREVIEW = 3  # 最大后文预览段落数

# ============ 重试配置 ============
DEFAULT_MAX_RETRIES = 3  # 默认最大重试次数
DEFAULT_RETRY_DELAY = 30  # 默认重试延迟（秒）

# ============ 批处理配置 ============
BATCH_PARAGRAPH_SIZE = 8  # 批量翻译时每批段落数

# ============ 术语表配置 ============
MAX_GLOSSARY_TERMS_IN_PROMPT = 15  # Prompt 中最大术语数量

# ============ 对话配置 ============
MAX_CONVERSATION_HISTORY = 5  # 对话历史最大消息数
