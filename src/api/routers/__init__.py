"""API router package exports."""

from .confirmation import router as confirmation_router
from .consistency import router as consistency_router
from .glossary import router as glossary_router
from .image_cleanup import router as image_cleanup_router
from .models import router as models_router
from .project_glossary import router as project_glossary_router
from .projects import router as projects_router
from .quality_report import router as quality_report_router
from .segmentation import router as segmentation_router
from .slack import router as slack_router
from .tasks import router as tasks_router
from .tools import router as tools_router
from .translate import router as translate_router

__all__ = [
    "confirmation_router",
    "consistency_router",
    "glossary_router",
    "models_router",
    "project_glossary_router",
    "projects_router",
    "quality_report_router",
    "segmentation_router",
    "slack_router",
    "tasks_router",
    "tools_router",
    "translate_router",
]
