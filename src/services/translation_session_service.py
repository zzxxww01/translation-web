"""Translation session management service.

Manages the lifecycle of translation sessions, including terminology snapshots,
change detection, and resume capabilities.
"""

from datetime import datetime, timezone
from pathlib import Path
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
            term_ids = self._get_active_term_ids(project_id)
            session.create_snapshot(term_ids)

        self._save_session(session)
        return session

    def start_session(self, session_id: str) -> TranslationSession:
        """Start a translation session.

        Args:
            session_id: Session identifier

        Returns:
            Updated session
        """
        session = self.load_session(session_id)
        session.update_status(SessionStatus.IN_PROGRESS)
        self._save_session(session)
        return session

    def pause_session(self, session_id: str) -> TranslationSession:
        """Pause a translation session.

        Args:
            session_id: Session identifier

        Returns:
            Updated session
        """
        session = self.load_session(session_id)
        session.update_status(SessionStatus.PAUSED)
        self._save_session(session)
        return session

    def complete_session(self, session_id: str) -> TranslationSession:
        """Mark a session as completed.

        Args:
            session_id: Session identifier

        Returns:
            Updated session
        """
        session = self.load_session(session_id)
        session.update_status(SessionStatus.COMPLETED)
        self._save_session(session)
        return session

    def fail_session(self, session_id: str) -> TranslationSession:
        """Mark a session as failed.

        Args:
            session_id: Session identifier

        Returns:
            Updated session
        """
        session = self.load_session(session_id)
        session.update_status(SessionStatus.FAILED)
        self._save_session(session)
        return session

    def detect_term_changes(
        self,
        session_id: str
    ) -> Tuple[List[TermChange], bool]:
        """Detect terminology changes since session snapshot.

        Args:
            session_id: Session identifier

        Returns:
            Tuple of (list of changes, has_changes flag)
        """
        session = self.load_session(session_id)

        if not session.snapshot_version:
            return [], False

        # Get current active terms
        current_term_ids = self._get_active_term_ids(session.project_id)
        snapshot_term_ids = set(session.term_ids)
        current_term_ids_set = set(current_term_ids)

        changes = []

        # Detect added terms
        for term_id in current_term_ids_set - snapshot_term_ids:
            term = self._load_term_by_id(term_id, session.project_id)
            if term:
                changes.append(TermChange(
                    term_id=term_id,
                    change_type="added",
                    new_value={"original": term.original, "translation": term.translation}
                ))

        # Detect deleted terms
        for term_id in snapshot_term_ids - current_term_ids_set:
            changes.append(TermChange(
                term_id=term_id,
                change_type="deleted"
            ))

        # Detect modified terms
        for term_id in snapshot_term_ids & current_term_ids_set:
            current_term = self._load_term_by_id(term_id, session.project_id)
            if current_term:
                # For simplicity, we consider any term in both sets as potentially modified
                # A more sophisticated implementation would compare actual content
                pass

        return changes, len(changes) > 0

    def refresh_snapshot(self, session_id: str) -> TranslationSession:
        """Refresh the terminology snapshot for a session.

        Args:
            session_id: Session identifier

        Returns:
            Updated session
        """
        session = self.load_session(session_id)
        term_ids = self._get_active_term_ids(session.project_id)
        session.create_snapshot(term_ids)
        self._save_session(session)
        return session

    def update_progress(
        self,
        session_id: str,
        progress_data: Dict
    ) -> TranslationSession:
        """Update session progress metadata.

        Args:
            session_id: Session identifier
            progress_data: Progress information to merge

        Returns:
            Updated session
        """
        session = self.load_session(session_id)
        session.progress.update(progress_data)
        session.updated_at = datetime.now(timezone.utc)
        self._save_session(session)
        return session

    def load_session(self, session_id: str) -> TranslationSession:
        """Load a session from disk.

        Args:
            session_id: Session identifier

        Returns:
            TranslationSession instance

        Raises:
            FileNotFoundError: If session file doesn't exist
        """
        session_file = self.sessions_dir / f"{session_id}.json"
        if not session_file.exists():
            raise FileNotFoundError(f"Session {session_id} not found")

        data = session_file.read_text(encoding='utf-8')
        import json
        return TranslationSession.model_validate_json(data)

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
                data = session_file.read_text(encoding='utf-8')
                import json
                session = TranslationSession.model_validate_json(data)

                if project_id and session.project_id != project_id:
                    continue
                if status and session.status != status:
                    continue

                sessions.append(session)
            except Exception:
                continue

        return sorted(sessions, key=lambda s: s.created_at, reverse=True)

    def _save_session(self, session: TranslationSession) -> None:
        """Save session to disk."""
        session_file = self.sessions_dir / f"{session.id}.json"
        session_file.write_text(session.model_dump_json(indent=2), encoding='utf-8')

    def _get_active_term_ids(self, project_id: str) -> List[str]:
        """Get all active term IDs for a project (global + project terms)."""
        term_ids = []

        # Load global terms
        global_terms = self.storage.load_terms(scope="global")
        term_ids.extend([t.id for t in global_terms if t.is_active()])

        # Load project terms
        project_terms = self.storage.load_terms(scope="project", project_id=project_id)
        term_ids.extend([t.id for t in project_terms if t.is_active()])

        return term_ids

    def _load_term_by_id(self, term_id: str, project_id: str) -> Optional[Term]:
        """Load a term by ID from global or project scope."""
        # Try global first
        global_terms = self.storage.load_terms(scope="global")
        for term in global_terms:
            if term.id == term_id:
                return term

        # Try project
        project_terms = self.storage.load_terms(scope="project", project_id=project_id)
        for term in project_terms:
            if term.id == term_id:
                return term

        return None
