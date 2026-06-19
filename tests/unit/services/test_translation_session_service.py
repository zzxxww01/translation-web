"""Tests for TranslationSessionService."""

import pytest
from pathlib import Path
from datetime import datetime

from src.models.session import SessionStatus, TranslationSession
from src.models.terminology import Term, TermMetadata
from src.services.translation_session_service import TranslationSessionService
from src.services.glossary_storage import GlossaryStorage


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for testing."""
    return tmp_path


@pytest.fixture
def storage(temp_dir):
    """Create a GlossaryStorage instance."""
    storage = GlossaryStorage(temp_dir)
    storage.initialize_storage()
    storage.initialize_storage(project_id="test-project")
    return storage


@pytest.fixture
def session_service(storage, temp_dir):
    """Create a TranslationSessionService instance."""
    return TranslationSessionService(storage, sessions_dir=temp_dir / "sessions")


class TestTranslationSessionService:
    """Test suite for TranslationSessionService."""

    def test_create_session_without_snapshot(self, session_service):
        """Test creating a session without terminology snapshot."""
        session = session_service.create_session(
            project_id="test-project",
            section_id="intro",
            create_snapshot=False
        )

        assert session.id is not None
        assert session.project_id == "test-project"
        assert session.section_id == "intro"
        assert session.status == SessionStatus.PENDING
        assert session.snapshot_version is None
        assert len(session.term_ids) == 0

    def test_create_session_with_snapshot(self, session_service, storage):
        """Test creating a session with terminology snapshot."""
        # Add some terms
        term1 = Term.create("AI", "人工智能", "global")
        metadata1 = TermMetadata(
            term_id=term1.id,
            term_original="AI",
            term_translation="人工智能",
            scope="global"
        )
        storage.add_term(term1, metadata1)

        session = session_service.create_session(
            project_id="test-project",
            create_snapshot=True
        )

        assert session.snapshot_version is not None
        assert len(session.term_ids) == 1
        assert term1.id in session.term_ids

    def test_start_session(self, session_service):
        """Test starting a session."""
        session = session_service.create_session("test-project", create_snapshot=False)

        updated = session_service.start_session(session.id)

        assert updated.status == SessionStatus.IN_PROGRESS
        assert updated.updated_at > session.updated_at

    def test_pause_session(self, session_service):
        """Test pausing a session."""
        session = session_service.create_session("test-project", create_snapshot=False)
        session_service.start_session(session.id)

        paused = session_service.pause_session(session.id)

        assert paused.status == SessionStatus.PAUSED

    def test_complete_session(self, session_service):
        """Test completing a session."""
        session = session_service.create_session("test-project", create_snapshot=False)
        session_service.start_session(session.id)

        completed = session_service.complete_session(session.id)

        assert completed.status == SessionStatus.COMPLETED
        assert completed.completed_at is not None

    def test_complete_session_persists_result_preview(self, session_service):
        """U3: complete_session 接受可选 result，落库为 result_preview（截断 500）。"""
        session = session_service.create_session("test-project", create_snapshot=False)
        completed = session_service.complete_session(session.id, "译文预览" * 200)
        assert completed.status == SessionStatus.COMPLETED
        assert completed.progress.get("result_preview") == ("译文预览" * 200)[:500]

    def test_fail_session_persists_error(self, session_service):
        """U3: fail_session 接受可选 error，落库到 progress。"""
        session = session_service.create_session("test-project", create_snapshot=False)
        failed = session_service.fail_session(session.id, "boom")
        assert failed.status == SessionStatus.FAILED
        assert failed.progress.get("error") == "boom"

    def test_get_session_terms_resolves_term_ids(self, session_service, storage):
        """U3: get_session_terms 把快照 term_ids 反查为 Term 对象。"""
        term = Term.create("GPU", "图形处理器", "global")
        meta = TermMetadata(term_id=term.id, term_original="GPU",
                            term_translation="图形处理器", scope="global")
        storage.add_term(term, meta)
        session = session_service.create_session("test-project", create_snapshot=True)

        terms = session_service.get_session_terms(session)

        assert [t.original for t in terms] == ["GPU"]


class TestFourStepSessionSignatureAlignment:
    """U3 回归：four_step 调用 session_service 的签名必须与真实 API 对齐。

    此前 four_step 用 create_session(source_text/target_language/include_snapshot)、
    get_session、session.terminology_snapshot 等不存在的 API，注入 session_service 后
    会直接 TypeError/AttributeError。本测试用真实 session_service 跑四步法保证不再发生。
    """

    def test_four_step_with_session_service_does_not_crash(self, session_service):
        from src.agents.context_manager import LayeredContextManager
        from src.agents.four_step_translator import FourStepTranslator
        from src.core.format_tokens import TranslationPayload
        from src.core.models import (
            Paragraph, ParagraphStatus, Section, SectionUnderstanding,
        )

        section = Section(
            section_id="intro", title="Intro",
            paragraphs=[Paragraph(id="p0", index=0, source="hi", status=ParagraphStatus.PENDING)],
        )
        tr = FourStepTranslator(object(), LayeredContextManager(),
                                session_service=session_service)
        # stub 各步骤，只验证 session 生命周期调用不报签名错误
        tr._step_understand = lambda *a, **k: SectionUnderstanding(
            role_in_article="body", relation_to_previous="", relation_to_next="",
            key_points=[], translation_notes=[])
        tr._translate_batch = lambda *a, **k: [TranslationPayload(text="你好")]
        tr._step_reflect = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("stop after draft"))

        # project_id 提供 → 创建会话；reflect 抛错 → 走降级，complete_session(session_id, result)
        result = tr.translate_section(section, [section], project_id="test-project")
        assert result.translations == ["你好"]

    def test_fail_session(self, session_service):
        """Test marking a session as failed."""
        session = session_service.create_session("test-project", create_snapshot=False)

        failed = session_service.fail_session(session.id)

        assert failed.status == SessionStatus.FAILED

    def test_detect_term_changes_no_changes(self, session_service, storage):
        """Test detecting term changes when there are none."""
        # Add term and create snapshot
        term1 = Term.create("AI", "人工智能", "global")
        metadata1 = TermMetadata(
            term_id=term1.id,
            term_original="AI",
            term_translation="人工智能",
            scope="global"
        )
        storage.add_term(term1, metadata1)

        session = session_service.create_session("test-project", create_snapshot=True)

        changes, has_changes = session_service.detect_term_changes(session.id)

        assert not has_changes
        assert len(changes) == 0

    def test_detect_term_changes_added(self, session_service, storage):
        """Test detecting added terms."""
        # Create session with snapshot
        session = session_service.create_session("test-project", create_snapshot=True)

        # Add new term after snapshot
        term1 = Term.create("GPU", "图形处理器", "global")
        metadata1 = TermMetadata(
            term_id=term1.id,
            term_original="GPU",
            term_translation="图形处理器",
            scope="global"
        )
        storage.add_term(term1, metadata1)

        changes, has_changes = session_service.detect_term_changes(session.id)

        assert has_changes
        assert len(changes) == 1
        assert changes[0].change_type == "added"
        assert changes[0].term_id == term1.id

    def test_detect_term_changes_deleted(self, session_service, storage):
        """Test detecting deleted terms."""
        # Add term
        term1 = Term.create("AI", "人工智能", "global")
        metadata1 = TermMetadata(
            term_id=term1.id,
            term_original="AI",
            term_translation="人工智能",
            scope="global"
        )
        storage.add_term(term1, metadata1)

        # Create session with snapshot
        session = session_service.create_session("test-project", create_snapshot=True)

        # Delete term
        storage.delete_term(term1.id, scope="global")

        changes, has_changes = session_service.detect_term_changes(session.id)

        assert has_changes
        assert len(changes) == 1
        assert changes[0].change_type == "deleted"
        assert changes[0].term_id == term1.id

    def test_refresh_snapshot(self, session_service, storage):
        """Test refreshing terminology snapshot."""
        session = session_service.create_session("test-project", create_snapshot=True)
        old_version = session.snapshot_version

        # Add new term
        term1 = Term.create("GPU", "图形处理器", "global")
        metadata1 = TermMetadata(
            term_id=term1.id,
            term_original="GPU",
            term_translation="图形处理器",
            scope="global"
        )
        storage.add_term(term1, metadata1)

        # Refresh snapshot
        updated = session_service.refresh_snapshot(session.id)

        assert updated.snapshot_version != old_version
        assert term1.id in updated.term_ids

    def test_update_progress(self, session_service):
        """Test updating session progress."""
        session = session_service.create_session("test-project", create_snapshot=False)

        updated = session_service.update_progress(session.id, {
            "current_step": 2,
            "total_steps": 4,
            "chunks_completed": 5
        })

        assert updated.progress["current_step"] == 2
        assert updated.progress["total_steps"] == 4
        assert updated.progress["chunks_completed"] == 5

    def test_load_session(self, session_service):
        """Test loading a session from disk."""
        session = session_service.create_session("test-project", create_snapshot=False)

        loaded = session_service.load_session(session.id)

        assert loaded.id == session.id
        assert loaded.project_id == session.project_id

    def test_load_session_not_found(self, session_service):
        """Test loading a non-existent session."""
        with pytest.raises(FileNotFoundError):
            session_service.load_session("non-existent-id")

    def test_list_sessions(self, session_service):
        """Test listing all sessions."""
        session1 = session_service.create_session("project-1", create_snapshot=False)
        session2 = session_service.create_session("project-2", create_snapshot=False)

        sessions = session_service.list_sessions()

        assert len(sessions) >= 2
        session_ids = [s.id for s in sessions]
        assert session1.id in session_ids
        assert session2.id in session_ids

    def test_list_sessions_filter_by_project(self, session_service):
        """Test listing sessions filtered by project."""
        session1 = session_service.create_session("project-1", create_snapshot=False)
        session2 = session_service.create_session("project-2", create_snapshot=False)

        sessions = session_service.list_sessions(project_id="project-1")

        assert len(sessions) == 1
        assert sessions[0].id == session1.id

    def test_list_sessions_filter_by_status(self, session_service):
        """Test listing sessions filtered by status."""
        session1 = session_service.create_session("project-1", create_snapshot=False)
        session2 = session_service.create_session("project-2", create_snapshot=False)
        session_service.complete_session(session2.id)

        sessions = session_service.list_sessions(status=SessionStatus.PENDING)

        assert len(sessions) == 1
        assert sessions[0].id == session1.id
