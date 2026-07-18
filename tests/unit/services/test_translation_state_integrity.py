import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from src.core.file_utils import read_json, write_json_atomic
from src.core.glossary import GlossaryManager
from src.core.models import (
    ArticleMetadata,
    Glossary,
    GlossaryTerm,
    Paragraph,
    ParagraphConfirmation,
    ProjectMeta,
    ProjectProgress,
    ProjectStatus,
    Section,
    TranslationStrategy,
    TranslationVersion,
)
from src.core.project import ProjectManager
from src.services.batch_translation_service import BatchTranslationService
from src.services.confirmation_service import ConfirmationService
from src.services.term_review_artifact import (
    SUBMISSION_PENDING,
    SUBMISSION_SUBMITTED,
    TERM_REVIEW_SCHEMA,
    TERM_REVIEW_SCHEMA_VERSION,
)
from src.services.terminology_review_service import TerminologyReviewService
from src.services.terminology_review_service import TermReviewArtifactConflict
from src.services.version_import_service import VersionImportService


def _project_meta() -> ProjectMeta:
    return ProjectMeta(
        id="demo",
        title="Demo",
        source_file="source.md",
        metadata=ArticleMetadata(subtitle="Original subtitle"),
    )


def test_batch_meta_merge_preserves_concurrent_progress_confirmations_and_versions(
    tmp_path,
) -> None:
    manager = ProjectManager(projects_path=str(tmp_path / "projects"))
    manager.save_meta(_project_meta())
    stale = manager.get("demo")

    latest = manager.get("demo")
    latest.progress = ProjectProgress(
        total_sections=2,
        total_paragraphs=8,
        approved=3,
        pending=5,
    )
    latest.versions = [
        TranslationVersion(
            id="reference",
            name="Reference",
            source_type="imported",
        )
    ]
    latest.confirmation_map["p1"] = ParagraphConfirmation(paragraph_id="p1")
    latest.metadata.authors = ["Concurrent author"]
    manager.save_meta(latest)

    stale.status = ProjectStatus.ANALYZING
    stale.title_translation = "演示"
    stale.metadata.subtitle = "译后副标题"
    service = BatchTranslationService.__new__(BatchTranslationService)
    service.project_manager = manager

    service._save_meta("demo", stale)
    service._save_meta(
        "demo",
        stale,
        fields=("title_translation",),
        metadata_fields=("subtitle",),
    )

    persisted = manager.get("demo")
    assert persisted.status == ProjectStatus.ANALYZING
    assert persisted.title_translation == "演示"
    assert persisted.metadata.subtitle == "译后副标题"
    assert persisted.metadata.authors == ["Concurrent author"]
    assert persisted.progress.approved == 3
    assert persisted.progress.total_paragraphs == 8
    assert [version.id for version in persisted.versions] == ["reference"]
    assert set(persisted.confirmation_map) == {"p1"}


def test_confirmation_meta_merge_does_not_roll_back_progress_or_other_state(
    tmp_path,
) -> None:
    manager = ProjectManager(projects_path=str(tmp_path / "projects"))
    manager.save_meta(_project_meta())
    stale = manager.get("demo")
    stale.confirmation_map["p2"] = ParagraphConfirmation(paragraph_id="p2")

    latest = manager.get("demo")
    latest.progress = ProjectProgress(
        total_sections=1,
        total_paragraphs=2,
        approved=1,
        pending=1,
    )
    latest.versions = [
        TranslationVersion(
            id="reference",
            name="Reference",
            source_type="imported",
        )
    ]
    latest.confirmation_map["p1"] = ParagraphConfirmation(paragraph_id="p1")
    manager.save_meta(latest)

    service = ConfirmationService.__new__(ConfirmationService)
    service.project_manager = manager
    service._save_meta("demo", stale, ["p2"])

    persisted = manager.get("demo")
    assert persisted.progress.approved == 1
    assert [version.id for version in persisted.versions] == ["reference"]
    assert set(persisted.confirmation_map) == {"p1", "p2"}


def test_version_upsert_preserves_other_project_metadata(tmp_path) -> None:
    manager = ProjectManager(projects_path=str(tmp_path / "projects"))
    meta = _project_meta()
    meta.progress = ProjectProgress(
        total_sections=1,
        total_paragraphs=2,
        approved=1,
        pending=1,
    )
    meta.confirmation_map["p1"] = ParagraphConfirmation(paragraph_id="p1")
    meta.versions.append(
        TranslationVersion(
            id="existing",
            name="Existing",
            source_type="imported",
        )
    )
    manager.save_meta(meta)

    manager.upsert_translation_version(
        "demo",
        TranslationVersion(
            id="new",
            name="New",
            source_type="imported",
        ),
    )

    persisted = manager.get("demo")
    assert persisted.progress.approved == 1
    assert set(persisted.confirmation_map) == {"p1"}
    assert [version.id for version in persisted.versions] == ["existing", "new"]


def test_reference_alignment_mutations_share_latest_version_snapshot(tmp_path) -> None:
    manager = ProjectManager(projects_path=str(tmp_path / "projects"))
    meta = _project_meta()
    meta.versions.append(
        TranslationVersion(
            id="reference",
            name="Reference",
            source_type="imported",
            paragraphs={"p1": None, "p2": None},
            metadata={
                "unaligned_items": [
                    {"ref_index": 10, "ref_text": "第一段"},
                    {"ref_index": 20, "ref_text": "第二段"},
                ]
            },
        )
    )
    manager.save_meta(meta)
    service = VersionImportService(manager)

    with ThreadPoolExecutor(max_workers=2) as executor:
        align_future = executor.submit(
            asyncio.run,
            service.manual_align("demo", "reference", 10, "p1"),
        )
        skip_future = executor.submit(
            asyncio.run,
            service.skip_unaligned("demo", "reference", 20),
        )
        align_future.result()
        skip_future.result()

    version = manager.get("demo").versions[0]
    assert version.paragraphs["p1"] == "第一段"
    assert version.metadata["unaligned_items"] == []
    assert version.metadata["aligned_count"] == 1
    assert version.metadata["unaligned_count"] == 0


@pytest.mark.asyncio
async def test_generated_title_does_not_overwrite_concurrent_manual_fields(
    tmp_path,
) -> None:
    manager = ProjectManager(projects_path=str(tmp_path / "projects"))
    manager.save_meta(_project_meta())
    stale_project = manager.get("demo")

    class EditingLLM:
        def translate_title(self, *args, **kwargs):
            manager.merge_meta_fields(
                "demo",
                fields={"title_translation": "人工标题"},
                nested_fields={"metadata": {"subtitle": "人工副标题"}},
            )
            return {"title": "AI 标题", "subtitle": "AI 副标题"}

    service = BatchTranslationService.__new__(BatchTranslationService)
    service.project_manager = manager
    service.llm = EditingLLM()
    service._build_title_glossary_block = lambda *args: ""
    analysis = SimpleNamespace(
        theme="Theme",
        structure_summary="Structure",
        style=SimpleNamespace(target_audience="Readers"),
    )

    await service._translate_title_and_metadata(stale_project, analysis)

    persisted = manager.get("demo")
    assert persisted.title_translation == "人工标题"
    assert persisted.metadata.subtitle == "人工副标题"
    assert stale_project.title_translation == "人工标题"
    assert stale_project.metadata.subtitle == "人工副标题"


def test_batch_glossary_seed_holds_project_lock_for_load_mutate_save() -> None:
    class TrackingGlossaryManager:
        def __init__(self) -> None:
            self.locked = False
            self.saved = False

        @contextmanager
        def project_lock(self, project_id: str):
            assert project_id == "demo"
            self.locked = True
            try:
                yield
            finally:
                self.locked = False

        def load_global(self) -> Glossary:
            return Glossary()

        def load_project(self, project_id: str) -> Glossary:
            assert self.locked
            return Glossary()

        def save_project(self, project_id: str, glossary: Glossary) -> None:
            assert self.locked
            assert glossary.get_term("chiplet") is not None
            self.saved = True

    glossary_manager = TrackingGlossaryManager()
    service = BatchTranslationService.__new__(BatchTranslationService)
    service.project_manager = SimpleNamespace(glossary_manager=glossary_manager)
    service._load_term_review_seed_terms = lambda project_id: [
        GlossaryTerm(
            original="chiplet",
            translation="芯粒",
            strategy=TranslationStrategy.TRANSLATE,
        )
    ]
    service._build_analysis_seed_terms = lambda analysis: []

    result = service._seed_project_glossary("demo", object())

    assert result["added"] == 1
    assert glossary_manager.saved is True


def test_term_review_pending_artifact_does_not_seed_until_submission(
    tmp_path,
) -> None:
    projects_path = tmp_path / "projects"
    manager = ProjectManager(projects_path=str(projects_path))
    manager.save_meta(_project_meta())
    manager.save_section_only(
        "demo",
        Section(
            section_id="s1",
            title="Architecture",
            paragraphs=[
                Paragraph(
                    id="p1",
                    index=0,
                    source="A chiplet connects to another chiplet.",
                )
            ],
        ),
    )
    glossary_manager = GlossaryManager(
        global_path=str(tmp_path / "glossary"),
        projects_path=str(projects_path),
    )
    manager.glossary_manager = glossary_manager

    class FakeLLM:
        @staticmethod
        def prescan_section_with_flash(**kwargs):
            return {
                "new_terms": [
                    {
                        "term": "chiplet",
                        "suggested_translation": "系统建议",
                        "context": "packaging architecture",
                    }
                ]
            }

    review_service = TerminologyReviewService(
        project_manager=manager,
        glossary_manager=glossary_manager,
        llm_provider=FakeLLM(),
    )
    payload = review_service.prepare_review("demo")
    batch_service = BatchTranslationService.__new__(BatchTranslationService)
    batch_service.project_manager = manager

    assert payload["schema"] == TERM_REVIEW_SCHEMA
    assert payload["schema_version"] == TERM_REVIEW_SCHEMA_VERSION
    assert payload["submission_status"] == SUBMISSION_PENDING
    assert payload["artifact_id"]
    assert batch_service._load_term_review_seed_terms("demo") == []

    review_service.apply_review(
        "demo",
        [
            {
                "term": "chiplet",
                "action": "accept",
                "translation": "芯粒",
            }
        ],
        artifact_id=payload["artifact_id"],
    )

    artifact = read_json(
        projects_path / "demo" / "artifacts" / "term-review" / "latest.json"
    )
    assert artifact["submission_status"] == SUBMISSION_SUBMITTED
    seed_terms = batch_service._load_term_review_seed_terms("demo")
    assert [(term.original, term.translation) for term in seed_terms] == [
        ("chiplet", "芯粒")
    ]


def test_term_review_rejects_submission_for_replaced_artifact(tmp_path) -> None:
    projects_path = tmp_path / "projects"
    manager = ProjectManager(projects_path=str(projects_path))
    manager.save_meta(_project_meta())
    manager.save_section_only(
        "demo",
        Section(
            section_id="s1",
            title="Architecture",
            paragraphs=[
                Paragraph(
                    id="p1",
                    index=0,
                    source="A chiplet connects to another chiplet.",
                )
            ],
        ),
    )
    glossary_manager = GlossaryManager(
        global_path=str(tmp_path / "glossary"),
        projects_path=str(projects_path),
    )

    class FakeLLM:
        @staticmethod
        def prescan_section_with_flash(**kwargs):
            return {
                "new_terms": [
                    {
                        "term": "chiplet",
                        "suggested_translation": "芯粒",
                        "context": "packaging architecture",
                    }
                ]
            }

    service = TerminologyReviewService(
        project_manager=manager,
        glossary_manager=glossary_manager,
        llm_provider=FakeLLM(),
    )
    first = service.prepare_review("demo")
    second = service.prepare_review("demo")

    with pytest.raises(TermReviewArtifactConflict):
        service.apply_review(
            "demo",
            [
                {
                    "term": "chiplet",
                    "action": "accept",
                    "translation": "错误串页译文",
                }
            ],
            artifact_id=first["artifact_id"],
        )

    assert first["artifact_id"] != second["artifact_id"]
    assert glossary_manager.load_project("demo").get_term("chiplet") is None
    persisted = read_json(
        projects_path / "demo" / "artifacts" / "term-review" / "latest.json"
    )
    assert persisted["artifact_id"] == second["artifact_id"]
    assert persisted["submission_status"] == SUBMISSION_PENDING


def test_term_review_loader_accepts_only_recognized_legacy_shape(tmp_path) -> None:
    projects_path = tmp_path / "projects"
    latest_path = (
        projects_path / "demo" / "artifacts" / "term-review" / "latest.json"
    )
    service = BatchTranslationService.__new__(BatchTranslationService)
    service.project_manager = SimpleNamespace(projects_path=projects_path)
    candidate = {
        "term": "CPO",
        "suggested_translation": "共封装光学",
        "reasons": ["title"],
        "occurrence_count": 1,
    }

    write_json_atomic(
        latest_path,
        {
            "project_id": "demo",
            "sections": [{"candidates": [candidate]}],
        },
    )
    assert [term.original for term in service._load_term_review_seed_terms("demo")] == [
        "CPO"
    ]

    write_json_atomic(
        latest_path,
        {
            "schema": "unknown.term-review",
            "schema_version": 99,
            "project_id": "demo",
            "sections": [{"candidates": [candidate]}],
        },
    )
    assert service._load_term_review_seed_terms("demo") == []


def test_apply_review_checks_project_before_creating_glossary(tmp_path) -> None:
    projects_path = tmp_path / "projects"
    manager = ProjectManager(projects_path=str(projects_path))
    glossary_manager = GlossaryManager(
        global_path=str(tmp_path / "glossary"),
        projects_path=str(projects_path),
    )
    service = TerminologyReviewService(
        project_manager=manager,
        glossary_manager=glossary_manager,
    )

    with pytest.raises(FileNotFoundError):
        service.apply_review(
            "missing",
            [
                {
                    "term": "chiplet",
                    "action": "accept",
                    "translation": "芯粒",
                }
            ],
        )

    assert not (projects_path / "missing").exists()
