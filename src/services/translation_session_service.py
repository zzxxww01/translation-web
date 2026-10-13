"""Translation session management service.

Manages the lifecycle of translation sessions, including terminology snapshots,
change detection, and resume capabilities.
"""

from datetime import datetime, timezone
from pathlib import Path
import logging
import re
import portalocker
from src.core.file_utils import write_text_atomic
from typing import Dict, List, Optional, Tuple

from src.models.session import SessionStatus, TermChange, TranslationSession
from src.models.terminology import Term
from src.services.glossary_storage import GlossaryStorage


class TranslationSessionService:
    """Service for managing translation sessions with terminology support."""

    def __init__(self, storage: GlossaryStorage, sessions_dir: Optional[Path] = None):
        """Initialize the session service.

        Args:
            storage: Glossary storage instance
            sessions_dir: Directory to store session files (defaults to storage.base_path / "sessions")
        """
        self.storage = storage
        self.sessions_dir = sessions_dir or (storage.base_path / "sessions")
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def create_session(
        self,
        project_id: str,
        section_id: Optional[str] = None,
        create_snapshot: bool = True
    ) -> TranslationSession:
        """Create a new translation session.

        Args:
            project_id: Project identifier
            section_id: Optional section identifier
            create_snapshot: Whether to create a terminology snapshot

        Returns:
            New TranslationSession instance
        """
        session = TranslationSession(
            project_id=project_id,
            section_id=section_id,
            status=SessionStatus.PENDING
        )

        if create_snapshot:
            terms = self._get_active_terms(project_id)
            session.create_snapshot(list(terms), terms)

        self._save_session(session)
        return session

    def start_session(self, session_id: str) -> TranslationSession:
        return self._mutate_session(session_id, lambda session: session.update_status(SessionStatus.IN_PROGRESS))

    def pause_session(self, session_id: str) -> TranslationSession:
        return self._mutate_session(session_id, lambda session: session.update_status(SessionStatus.PAUSED))

    def complete_session(self, session_id: str, result: Optional[str] = None) -> TranslationSession:
        def complete(session):
            session.update_status(SessionStatus.COMPLETED)
            if result is not None:
                session.progress["result_preview"] = result[:500]
        return self._mutate_session(session_id, complete)

    def fail_session(self, session_id: str, error: Optional[str] = None) -> TranslationSession:
        def fail(session):
            session.update_status(SessionStatus.FAILED)
            if error is not None:
                session.progress["error"] = str(error)
        return self._mutate_session(session_id, fail)

    def get_session_terms(self, session: TranslationSession) -> List[Term]:
        """New sessions validate against saved definitions, not today's glossary."""
        if session.snapshot_terms is not None:
            if set(session.snapshot_terms) != set(session.term_ids):
                raise ValueError("Session snapshot identities are inconsistent")
            return [session.snapshot_terms[key].model_copy(deep=True) for key in session.term_ids]
        # Legacy records did not store definitions. Preserve read compatibility,
        # but do not pretend a current lookup is a historical content snapshot.
        logging.getLogger(__name__).warning("Session %s has an ID-only legacy terminology snapshot", session.id)
        current = self._get_active_terms(session.project_id)
        return [current[key].model_copy(deep=True) for key in session.term_ids if key in current]

    def detect_term_changes(self, session_id: str) -> Tuple[List[TermChange], bool]:
        session = self.load_session(session_id)
        if not session.snapshot_version:
            return [], False
        current = self._get_active_terms(session.project_id)
        previous_ids = set(session.term_ids)
        changes = []
        for key in sorted(set(current) - previous_ids):
            changes.append(TermChange(term_id=key, change_type="added", new_value=current[key].model_dump(mode="json")))
        for key in sorted(previous_ids - set(current)):
            previous = (session.snapshot_terms or {}).get(key)
            changes.append(TermChange(term_id=key, change_type="deleted", old_value=previous.model_dump(mode="json") if previous else None))
        if session.snapshot_terms is not None:
            for key in sorted(previous_ids & set(current)):
                previous = session.snapshot_terms.get(key)
                if previous is None:
                    raise ValueError("Session snapshot is incomplete")
                old, new = previous.model_dump(mode="json"), current[key].model_dump(mode="json")
                if old != new:
                    changes.append(TermChange(term_id=key, change_type="modified", old_value=old, new_value=new))
        else:
            logging.getLogger(__name__).warning("Legacy session %s cannot detect same-ID definition changes", session.id)
        return changes, bool(changes)

    def refresh_snapshot(self, session_id: str) -> TranslationSession:
        def refresh(session):
            terms = self._get_active_terms(session.project_id)
            session.create_snapshot(list(terms), terms)
        return self._mutate_session(session_id, refresh)

    def update_progress(self, session_id: str, progress_data: Dict) -> TranslationSession:
        def update(session):
            session.progress.update(progress_data)
            session.updated_at = datetime.now(timezone.utc)
        return self._mutate_session(session_id, update)

    def load_session(self, session_id: str) -> TranslationSession:
        path = self._session_path(session_id)
        if not path.exists():
            raise FileNotFoundError(f"Session {session_id} not found")
        session = TranslationSession.model_validate_json(path.read_text(encoding="utf-8"))
        if session.id != session_id:
            raise ValueError("Stored session identity does not match its file")
        return session

    def list_sessions(
        self,
        project_id: Optional[str] = None,
        status: Optional[SessionStatus] = None
    ) -> List[TranslationSession]:
        """List sessions with optional filters.

        Args:
            project_id: Filter by project
            status: Filter by status

        Returns:
            List of matching sessions
        """
        sessions = []
        for session_file in self.sessions_dir.glob("*.json"):
            try:
                session = self.load_session(session_file.stem)

                if project_id and session.project_id != project_id:
                    continue
                if status and session.status != status:
                    continue

                sessions.append(session)
            except Exception:
                continue

        return sorted(sessions, key=lambda s: s.created_at.timestamp(), reverse=True)

    def _save_session(self, session: TranslationSession) -> None:
        write_text_atomic(self._session_path(session.id), session.model_dump_json(indent=2))

    def _session_path(self, session_id: str) -> Path:
        if not isinstance(session_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", session_id):
            raise ValueError("Invalid session ID")
        root = self.sessions_dir.resolve()
        path = root / f"{session_id}.json"
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError("Session file is outside its storage root")
        return path

    def _mutate_session(self, session_id: str, mutate) -> TranslationSession:
        path = self._session_path(session_id)
        lock_path = path.with_suffix(".json.lock")
        if lock_path.is_symlink():
            raise ValueError("Invalid session lock")
        # A lock around only the final write is not enough: the read must be
        # protected too, including across independently created service objects.
        with portalocker.Lock(str(lock_path), timeout=10):
            session = self.load_session(session_id)
            mutate(session)
            self._save_session(session)
            return session

    def _get_active_terms(self, project_id: str) -> Dict[str, Term]:
        terms = [*self.storage.load_terms(scope="global"),
                 *self.storage.load_terms(scope="project", project_id=project_id)]
        return {term.id: term.model_copy(deep=True) for term in terms if term.is_active()}

    def _get_active_term_ids(self, project_id: str) -> List[str]:
        return list(self._get_active_terms(project_id))

    def _load_term_by_id(self, term_id: str, project_id: str) -> Optional[Term]:
        return self._get_active_terms(project_id).get(term_id)
