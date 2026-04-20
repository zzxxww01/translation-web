"""
Slack router entrypoint.

Keeps public import path stable while splitting implementation by domain.
"""

from fastapi import APIRouter

from .slack_compose import router as slack_compose_router
from .slack_process import router as slack_process_router
from .slack_refine import router as slack_refine_router
from .slack_refine_version import router as slack_refine_version_router
from .slack_sync_optimize import router as slack_sync_optimize_router


router = APIRouter(prefix="", tags=["slack"])
router.include_router(slack_process_router)
router.include_router(slack_compose_router)
router.include_router(slack_refine_router)
router.include_router(slack_refine_version_router)
router.include_router(slack_sync_optimize_router)
