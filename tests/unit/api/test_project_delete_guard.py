from unittest.mock import Mock

import pytest
from starlette.requests import Request

from src.api.middleware import ConflictException
from src.api.routers.projects_management import delete_project
from src.services.translation_run_registry import translation_run_registry


def _delete_request(project_id: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "DELETE",
            "path": f"/api/projects/{project_id}",
            "headers": [],
            "client": ("127.0.0.1", 50000),
        }
    )


@pytest.mark.asyncio
async def test_delete_rejects_project_with_active_translation() -> None:
    project_id = "active-delete-guard"
    translation_run_registry.release_active_run(project_id)
    acquired = await translation_run_registry.claim_translation_slot(project_id)
    assert acquired["status"] == "acquired"
    project_manager = Mock()

    try:
        with pytest.raises(
            ConflictException,
            match="active translation",
        ) as raised:
            await delete_project(
                _delete_request(project_id),
                project_id,
                project_manager,
            )
    finally:
        translation_run_registry.release_active_run(project_id)

    assert raised.value.error_code == "PROJECT_TRANSLATION_ACTIVE"
    project_manager.delete.assert_not_called()
