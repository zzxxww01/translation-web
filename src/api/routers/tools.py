"""
Tools router entrypoint.

Keeps public import path stable while splitting implementation by domain.
"""

from fastapi import APIRouter

from .tools_email import router as tools_email_router
from .tools_timezone import router as tools_timezone_router
from .tools_translate import router as tools_translate_router


router = APIRouter(prefix="/tools", tags=["tools"])
router.include_router(tools_translate_router)
router.include_router(tools_email_router)
router.include_router(tools_timezone_router)
