"""
Confirmation router entrypoint.

Keeps public import path stable while splitting implementation by domain.
"""

from fastapi import APIRouter

from .confirmation_translation import router as confirmation_translation_router
from .confirmation_versions import router as confirmation_versions_router


router = APIRouter(prefix="/projects", tags=["confirmation"])
router.include_router(confirmation_translation_router)
router.include_router(confirmation_versions_router)
