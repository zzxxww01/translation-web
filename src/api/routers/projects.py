"""
Projects router entrypoint.

Keeps public import path stable while splitting implementation by domain.
"""

from fastapi import APIRouter

from .projects_management import router as projects_management_router
from .projects_paragraphs import router as projects_paragraphs_router


router = APIRouter(prefix="", tags=["projects"])
router.include_router(projects_management_router)
router.include_router(projects_paragraphs_router)
