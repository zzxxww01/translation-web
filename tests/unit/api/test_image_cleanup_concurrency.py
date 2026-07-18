from contextlib import nullcontext

from src.api.routers.image_cleanup import (
    ImageCleanupRequest,
    _cleanup_image_paragraphs_sync,
)
from src.core.models import Paragraph, Section


class SnapshotProjectManager:
    def __init__(self, stale: Section, latest: Section) -> None:
        self.stale = stale
        self.latest = latest
        self.saved = None
        self.progress_updates = 0

    def get(self, _project_id):
        return object()

    def get_sections(self, _project_id):
        return [self.stale.model_copy(deep=True)]

    def section_lock(self, _project_id, _section_id):
        return nullcontext()

    def get_section(self, _project_id, _section_id):
        return self.latest.model_copy(deep=True)

    def save_section_only(self, _project_id, section):
        self.saved = section.model_copy(deep=True)

    def update_progress(self, _project_id):
        self.progress_updates += 1


def test_cleanup_reloads_section_before_write_and_preserves_recent_translation():
    stale_paragraph = Paragraph(
        id="p1",
        index=0,
        source="![chart](chart.png)",
    )
    stale_paragraph.add_translation("Cannot translate image", "old")
    stale = Section(
        section_id="s1",
        title="Chart",
        paragraphs=[stale_paragraph],
    )

    latest = stale.model_copy(deep=True)
    latest.paragraphs[0].add_translation("人工补充的图表说明", "manual")
    manager = SnapshotProjectManager(stale, latest)

    result = _cleanup_image_paragraphs_sync(
        "demo",
        ImageCleanupRequest(),
        manager,
    )

    assert result.cleaned_translations == 1
    assert manager.saved is not None
    assert set(manager.saved.paragraphs[0].translations) == {"manual"}
    assert manager.saved.paragraphs[0].translations["manual"].text == "人工补充的图表说明"
    assert manager.progress_updates == 1
