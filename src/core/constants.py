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
MAX_GLOSSARY_TERMS_IN_PROMPT = 30  # Prompt 中最大术语数量
MAX_REVIEW_TERMS_IN_PROMPT = 10  # 反思/润色阶段的关键术语数量
MAX_LEARNED_RULES_IN_PROMPT = 20  # Prompt 中最大已学习规则条数
MAX_LEARNED_RULES_CHARS = 600  # Prompt 中已学习规则的总字符上限

# ============ 长文上下文配置 ============
MAX_ARTICLE_GUIDELINES_IN_PROMPT = 6  # 长文翻译阶段注入的全局指南数量
MAX_SECTION_KEY_POINTS_IN_PROMPT = 4  # 章节核心论点数量
MAX_SECTION_NOTES_IN_PROMPT = 4  # 章节翻译注意事项数量
MAX_ARTICLE_CHALLENGES_IN_PROMPT = 4  # 全文高风险挑战数量
MAX_REVIEW_PRIORITIES_IN_PROMPT = 5  # 反思阶段优先级条数
MAX_STYLE_NOTES_IN_PROMPT = 4  # 风格说明附加条数
MAX_FORMAT_TOKENS_IN_PROMPT = 6  # 格式 token 预览数量
MAX_HEADING_CHAIN_IN_PROMPT = 4  # 标题链保留数量
MAX_SECTION_GUIDELINE_LINES_IN_PROMPT = 10  # section batch prompt 的 guideline 总行数

# ============ 对话配置 ============
MAX_CONVERSATION_HISTORY = 5  # 对话历史最大消息数
