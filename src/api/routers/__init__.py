"""
API Routers Package

包含所有 API 路由模块：
- tasks: 任务管理
- conversations: 对话管理
- slack: Slack 助手
- translate: 翻译服务
- tools: 工具箱（文本翻译、邮件回复、时区转换等）
- projects: 项目管理（项目、章节、段落、术语表）
- confirmation: 分段确认工作流
- consistency: 一致性审查
- segmentation: 分段策略预览
"""

from .tasks import router as tasks_router
from .conversations import router as conversations_router
from .slack import router as slack_router
from .translate import router as translate_router
from .tools import router as tools_router
from .glossary import router as glossary_router
from .project_glossary import router as project_glossary_router
from .projects import router as projects_router
from .confirmation import router as confirmation_router
from .consistency import router as consistency_router
from .segmentation import router as segmentation_router

__all__ = [
    "tasks_router",
    "conversations_router",
    "slack_router",
    "translate_router",
    "tools_router",
    "glossary_router",
    "project_glossary_router",
    "projects_router",
    "confirmation_router",
    "consistency_router",
    "segmentation_router",
]
