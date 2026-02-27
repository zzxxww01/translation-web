"""
Translate router entrypoint.

Keeps public import path stable while splitting implementation by domain.
"""

from fastapi import APIRouter

from .translate_posts import router as translate_posts_router
from .translate_projects import router as translate_projects_router


router = APIRouter(prefix="", tags=["translate"])
router.include_router(translate_posts_router)
router.include_router(translate_projects_router)
