import pytest

from src.api.routers.translate_models import ResolveConflictRequest
from src.api.routers.translate_projects import resolve_term_conflict_live


@pytest.mark.asyncio
async def test_resolve_term_conflict_live_uses_request_payload_fields():
    response = await resolve_term_conflict_live(
        "demo-project",
        ResolveConflictRequest(
            term="GPU",
            chosen_translation="图形处理器",
            apply_to_all=True,
        ),
    )

    assert response == {
        "status": "accepted",
        "term": "GPU",
        "chosen": "图形处理器",
    }
