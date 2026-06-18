"""Glossary storage service for term and metadata management.

This module provides CRUD operations for terms, metadata, and decision audit logs
with file locking, atomic writes, and soft deletion support.
"""

import json
import logging
import os
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import portalocker
    HAS_PORTALOCKER = True
except ImportError:
    HAS_PORTALOCKER = False

from src.models.terminology import DecisionRecord, Term, TermMetadata

logger = logging.getLogger(__name__)

# Process-wide registry of per-file in-process locks. Used to serialize reads
# and writes to the same JSON file across threads (and across GlossaryStorage
# instances) within a single process. portalocker provides cross-process
# locking when available; this guards the common in-process case and is the
# only available mutual exclusion on the no-portalocker fallback path, where a
# concurrent reader's open handle would otherwise make the writer's atomic
# replace() fail on Windows.
_FILE_LOCKS: Dict[str, threading.Lock] = {}
_FILE_LOCKS_GUARD = threading.Lock()


def _get_inproc_lock(path: Path) -> threading.Lock:
    """Return a stable per-path in-process lock (keyed by absolute path)."""
    key = str(path.resolve()) if path.is_absolute() else str(Path(os.path.abspath(path)))
    with _FILE_LOCKS_GUARD:
        lock = _FILE_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _FILE_LOCKS[key] = lock
        return lock


class GlossaryStorage:
    """Storage service for glossary terms and metadata.

    Provides thread-safe CRUD operations with file locking, atomic writes,
    and comprehensive audit logging.

    Attributes:
        base_path: Root directory for all glossary data
        global_path: Path to global glossary directory
    """

    def __init__(self, base_path: Path):
        """Initialize storage service.

        Args:
            base_path: Root directory for glossary storage
        """
        self.base_path = Path(base_path)
        self.global_path = self.base_path / "glossary"

    def initialize_storage(self, project_id: Optional[str] = None) -> None:
        """Initialize storage structure.

        Creates necessary directories and empty JSON files for either global
        or project-specific glossary storage. Safe to call multiple times -
        will not overwrite existing data.

        Args:
            project_id: Project ID, None for global glossary initialization

        Raises:
            PermissionError: If directories or files cannot be created
        """
        if project_id:
            # Initialize project directory structure
            project_path = self.base_path / "projects" / project_id
            (project_path / "glossary" / "sessions").mkdir(parents=True, exist_ok=True)
            (project_path / "artifacts" / "term-extraction").mkdir(parents=True, exist_ok=True)
            (project_path / "artifacts" / "audit").mkdir(parents=True, exist_ok=True)

            # Create empty JSON files if they don't exist
            for file in ["glossary/terms.json", "glossary/metadata.json"]:
                file_path = project_path / file
                if not file_path.exists():
                    file_path.write_text("[]", encoding='utf-8')

            logger.info(f"Initialized project glossary storage: {project_id}")
        else:
            # Initialize global directory structure
            global_path = self.base_path / "glossary"
            (global_path / "audit").mkdir(parents=True, exist_ok=True)

            # Create empty JSON files if they don't exist
            for file in ["terms.json", "metadata.json"]:
                file_path = global_path / file
                if not file_path.exists():
                    file_path.write_text("[]", encoding='utf-8')

            logger.info("Initialized global glossary storage")

    def _get_project_path(self, project_id: str) -> Path:
        """Get project glossary directory path.

        Args:
            project_id: Project identifier

        Returns:
            Path to project glossary directory
        """
        return self.base_path / "projects" / project_id / "glossary"

    def _get_terms_path(self, scope: str, project_id: Optional[str] = None) -> Path:
        """Get terms.json file path.

        Args:
            scope: Either "global" or "project"
            project_id: Required when scope is "project"

        Returns:
            Path to terms.json file
        """
        if scope == "global":
            return self.global_path / "terms.json"
        else:
            if not project_id:
                raise ValueError("project_id is required when scope is 'project'")
            return self._get_project_path(project_id) / "terms.json"

    def _get_metadata_path(self, scope: str, project_id: Optional[str] = None) -> Path:
        """Get metadata.json file path.

        Args:
            scope: Either "global" or "project"
            project_id: Required when scope is "project"

        Returns:
            Path to metadata.json file
        """
        if scope == "global":
            return self.global_path / "metadata.json"
        else:
            if not project_id:
                raise ValueError("project_id is required when scope is 'project'")
            return self._get_project_path(project_id) / "metadata.json"

    def _get_decisions_path(self, scope: str, project_id: Optional[str] = None) -> Path:
        """Get decisions.jsonl file path.

        Args:
            scope: Either "global" or "project"
            project_id: Required when scope is "project"

        Returns:
            Path to decisions.jsonl file
        """
        if scope == "global":
            return self.global_path / "audit" / "decisions.jsonl"
        else:
            if not project_id:
                raise ValueError("project_id is required when scope is 'project'")
            return self.base_path / "projects" / project_id / "artifacts" / "audit" / "decisions.jsonl"

    def _get_lock_path(self, path: Path) -> Path:
        """Get the sidecar lock-file path used to serialize reads and writes.

        Both readers and writers acquire this single ``<file>.lock`` so they
        mutually exclude. Locking the data file directly (read) and the temp
        file (write) does NOT mutually exclude, and on Windows a read handle
        held open on the target blocks ``temp.replace(target)`` with a
        PermissionError. Using one independent lock file avoids both problems.
        """
        return path.with_suffix(path.suffix + '.lock')

    def _read_json_with_lock(self, path: Path, default: list) -> list:
        """Read JSON file under the shared sidecar lock.

        The lock file is held only long enough to read the target into memory;
        the target's own handle is closed immediately (not held), so it never
        blocks a concurrent writer's atomic replace on Windows.

        Args:
            path: Path to JSON file
            default: Default value if file doesn't exist

        Returns:
            Parsed JSON data

        Raises:
            ValueError: If JSON is malformed
            PermissionError: If file cannot be accessed
        """
        if not path.exists():
            return default

        def _read_target() -> list:
            # Read target into memory and close the handle ASAP (do not hold it).
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except FileNotFoundError:
                # Target may have been replaced/removed between the existence
                # check and the open; treat as empty rather than erroring.
                return default
            if not content.strip():
                return default
            return json.loads(content)

        lock_path = self._get_lock_path(path)

        # In-process lock serializes threads regardless of portalocker.
        with _get_inproc_lock(path):
            if HAS_PORTALOCKER:
                try:
                    with portalocker.Lock(lock_path, 'w', timeout=10):
                        return _read_target()
                except portalocker.exceptions.LockException as e:
                    raise PermissionError(f"Failed to acquire lock on {lock_path}: {e}")
            else:
                # Fallback: in-process lock above already serializes readers vs
                # writers; retry covers transient OS errors.
                for attempt in range(3):
                    try:
                        return _read_target()
                    except (IOError, OSError) as e:
                        if attempt == 2:
                            raise PermissionError(f"Failed to read {path} after 3 attempts: {e}")
                        time.sleep(0.1 * (attempt + 1))

        return default

    def _write_json_with_lock(self, path: Path, data: list) -> None:
        """Write JSON file atomically under the shared sidecar lock.

        Holds ``<file>.lock`` (the same lock readers use) for the entire
        write-temp-then-replace sequence, so it is mutually exclusive with
        readers and other writers. Each write uses a uniquely-named temp file
        in the target directory (so concurrent writers never collide on a
        shared ``.tmp`` name), and PermissionError from the replace itself is
        handled (with orphan-temp cleanup) instead of escaping uncaught.

        Args:
            path: Path to JSON file
            data: Data to write

        Raises:
            PermissionError: If file cannot be written
        """
        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        # Serialize data with datetime handling
        json_data = json.dumps(data, ensure_ascii=False, indent=2, default=str)

        def _atomic_write() -> None:
            # Unique temp name in the same directory => same filesystem, so
            # replace() is atomic and concurrent writers don't share a name.
            fd, tmp_name = tempfile.mkstemp(
                dir=str(path.parent), prefix=path.name + '.', suffix='.tmp'
            )
            temp_path = Path(tmp_name)
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    f.write(json_data)
                # replace() can raise PermissionError on Windows if the target
                # is momentarily held open; surface it as PermissionError after
                # cleaning up the temp file rather than leaving an orphan.
                temp_path.replace(path)
            except Exception:
                if temp_path.exists():
                    try:
                        temp_path.unlink()
                    except OSError:
                        pass
                raise

        lock_path = self._get_lock_path(path)

        # In-process lock serializes threads regardless of portalocker; this is
        # what prevents a concurrent reader's open handle from making the
        # replace() below fail with PermissionError on Windows.
        with _get_inproc_lock(path):
            if HAS_PORTALOCKER:
                try:
                    with portalocker.Lock(lock_path, 'w', timeout=10):
                        _atomic_write()
                except portalocker.exceptions.LockException as e:
                    raise PermissionError(f"Failed to acquire lock on {lock_path}: {e}")
                except PermissionError:
                    raise
                except OSError as e:
                    raise PermissionError(f"Failed to write {path}: {e}")
            else:
                # Fallback: in-process lock above serializes writers vs readers;
                # retry covers transient OS errors (e.g. AV/indexer touching it).
                for attempt in range(3):
                    try:
                        _atomic_write()
                        break
                    except (IOError, OSError) as e:
                        if attempt == 2:
                            raise PermissionError(f"Failed to write {path} after 3 attempts: {e}")
                        time.sleep(0.1 * (attempt + 1))

    # === Term CRUD ===

    def load_terms(self, scope: str, project_id: Optional[str] = None) -> List[Term]:
        """Load terms from storage.

        Args:
            scope: Either "global" or "project"
            project_id: Required when scope is "project"

        Returns:
            List of Term objects

        Raises:
            ValueError: If JSON is malformed
            PermissionError: If file cannot be accessed
        """
        path = self._get_terms_path(scope, project_id)
        data = self._read_json_with_lock(path, [])
        return [Term(**item) for item in data]

    def save_terms(self, terms: List[Term], scope: str, project_id: Optional[str] = None) -> None:
        """Save terms to storage (overwrites existing).

        Args:
            terms: List of Term objects to save
            scope: Either "global" or "project"
            project_id: Required when scope is "project"

        Raises:
            PermissionError: If file cannot be written
        """
        path = self._get_terms_path(scope, project_id)
        data = [term.model_dump() for term in terms]
        self._write_json_with_lock(path, data)

    def get_term(self, term_id: str, scope: str, project_id: Optional[str] = None) -> Optional[Term]:
        """Get a single term by ID.

        Args:
            term_id: Term identifier
            scope: Either "global" or "project"
            project_id: Required when scope is "project"

        Returns:
            Term object if found, None otherwise
        """
        terms = self.load_terms(scope, project_id)
        for term in terms:
            if term.id == term_id:
                return term
        return None

    def add_term(self, term: Term, metadata: TermMetadata) -> Term:
        """Add a new term (atomic operation with rollback).

        Args:
            term: Term object to add
            metadata: Associated metadata

        Returns:
            The added Term object

        Raises:
            ValueError: If term with same ID already exists
            PermissionError: If files cannot be written
        """
        scope = metadata.scope
        project_id = metadata.project_id

        # Load existing data
        terms = self.load_terms(scope, project_id)
        metadata_list = self.load_metadata(scope, project_id)

        # Check for duplicates
        if any(t.id == term.id for t in terms):
            raise ValueError(f"Term with id {term.id} already exists")

        # Backup original data for rollback
        original_terms = terms.copy()
        original_metadata = metadata_list.copy()

        try:
            # Add term
            terms.append(term)
            self.save_terms(terms, scope, project_id)

            # Add metadata
            metadata_list.append(metadata)
            self.save_metadata(metadata_list, scope, project_id)

            logger.info(f"Added term: {term.original} ({term.id}) in {scope} scope")
            return term

        except Exception as e:
            # Rollback on failure
            logger.error(f"Failed to add term {term.id}, rolling back: {e}")
            try:
                self.save_terms(original_terms, scope, project_id)
                self.save_metadata(original_metadata, scope, project_id)
                logger.info(f"Rollback successful for term {term.id}")
            except Exception as rollback_error:
                logger.critical(f"ROLLBACK FAILED for term {term.id}: {rollback_error}")
            raise

    def update_term(self, term: Term, metadata: TermMetadata, changes: dict) -> Term:
        """Update an existing term (atomic operation with rollback).

        Args:
            term: Updated Term object
            metadata: Updated metadata
            changes: Dictionary of changes for audit log

        Returns:
            The updated Term object

        Raises:
            ValueError: If term doesn't exist
            PermissionError: If files cannot be written
        """
        scope = metadata.scope
        project_id = metadata.project_id

        # Load existing data
        terms = self.load_terms(scope, project_id)
        metadata_list = self.load_metadata(scope, project_id)

        # Backup original data for rollback
        original_terms = terms.copy()
        original_metadata = metadata_list.copy()

        # Find term
        found = False
        for i, t in enumerate(terms):
            if t.id == term.id:
                terms[i] = term
                found = True
                break

        if not found:
            raise ValueError(f"Term with id {term.id} not found")

        try:
            # Update term
            self.save_terms(terms, scope, project_id)

            # Update metadata
            metadata.updated_at = datetime.now(timezone.utc)
            for i, m in enumerate(metadata_list):
                if m.term_id == term.id:
                    metadata_list[i] = metadata
                    break

            self.save_metadata(metadata_list, scope, project_id)

            logger.info(f"Updated term: {term.original} ({term.id})")
            return term

        except Exception as e:
            # Rollback on failure
            logger.error(f"Failed to update term {term.id}, rolling back: {e}")
            try:
                self.save_terms(original_terms, scope, project_id)
                self.save_metadata(original_metadata, scope, project_id)
                logger.info(f"Rollback successful for term {term.id}")
            except Exception as rollback_error:
                logger.critical(f"ROLLBACK FAILED for term {term.id}: {rollback_error}")
            raise

        logger.info(f"Updated term: {term.original} ({term.id})")
        return term

    def delete_term(self, term_id: str, scope: str, project_id: Optional[str] = None, reason: str = "") -> None:
        """Soft delete a term.

        Updates Term.status to "inactive" and TermMetadata.is_deleted to True.

        Args:
            term_id: Term identifier
            scope: Either "global" or "project"
            project_id: Required when scope is "project"
            reason: Reason for deletion (for audit log)

        Raises:
            ValueError: If term doesn't exist
            PermissionError: If files cannot be written
        """
        # Update term status
        terms = self.load_terms(scope, project_id)
        term = None
        for t in terms:
            if t.id == term_id:
                t.status = "inactive"
                term = t
                break

        if not term:
            raise ValueError(f"Term with id {term_id} not found")

        self.save_terms(terms, scope, project_id)

        # Update metadata
        metadata_list = self.load_metadata(scope, project_id)
        metadata = None
        for m in metadata_list:
            if m.term_id == term_id:
                m.mark_deleted()
                metadata = m
                break

        self.save_metadata(metadata_list, scope, project_id)

        # Log decision
        if metadata:
            record = DecisionRecord(
                session_id="system",
                project_id=project_id or "global",
                term_original=term.original,
                action="skip",
                reason=reason or "Soft deleted"
            )
            self.append_decision(record, scope, project_id)

        logger.info(f"Deleted term: {term.original} ({term_id})")

    # === Metadata CRUD ===

    def load_metadata(self, scope: str, project_id: Optional[str] = None) -> List[TermMetadata]:
        """Load metadata from storage.

        Args:
            scope: Either "global" or "project"
            project_id: Required when scope is "project"

        Returns:
            List of TermMetadata objects

        Raises:
            ValueError: If JSON is malformed
            PermissionError: If file cannot be accessed
        """
        path = self._get_metadata_path(scope, project_id)
        data = self._read_json_with_lock(path, [])
        return [TermMetadata(**item) for item in data]

    def save_metadata(self, metadata_list: List[TermMetadata], scope: str, project_id: Optional[str] = None) -> None:
        """Save metadata to storage (overwrites existing).

        Args:
            metadata_list: List of TermMetadata objects to save
            scope: Either "global" or "project"
            project_id: Required when scope is "project"

        Raises:
            PermissionError: If file cannot be written
        """
        path = self._get_metadata_path(scope, project_id)
        data = [m.model_dump() for m in metadata_list]
        self._write_json_with_lock(path, data)

    def get_metadata(self, term_id: str, scope: str, project_id: Optional[str] = None) -> Optional[TermMetadata]:
        """Get metadata for a term.

        Args:
            term_id: Term identifier
            scope: Either "global" or "project"
            project_id: Required when scope is "project"

        Returns:
            TermMetadata object if found, None otherwise
        """
        metadata_list = self.load_metadata(scope, project_id)
        for metadata in metadata_list:
            if metadata.term_id == term_id:
                return metadata
        return None

    # === Audit Log ===

    def append_decision(self, record: DecisionRecord, scope: str, project_id: Optional[str] = None) -> None:
        """Append a decision record to audit log.

        Args:
            record: DecisionRecord to append
            scope: Either "global" or "project"
            project_id: Required when scope is "project"

        Raises:
            PermissionError: If file cannot be written
        """
        path = self._get_decisions_path(scope, project_id)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Serialize record with datetime handling
        json_line = json.dumps(record.model_dump(), ensure_ascii=False, default=str) + "\n"

        # Append to JSONL file
        if HAS_PORTALOCKER:
            try:
                with portalocker.Lock(path, 'a', timeout=10) as f:
                    f.write(json_line)
            except portalocker.exceptions.LockException as e:
                raise PermissionError(f"Failed to acquire lock on {path}: {e}")
        else:
            # Fallback: simple retry mechanism
            for attempt in range(3):
                try:
                    with open(path, 'a', encoding='utf-8') as f:
                        f.write(json_line)
                    break
                except (IOError, OSError) as e:
                    if attempt == 2:
                        raise PermissionError(f"Failed to append to {path} after 3 attempts: {e}")
                    time.sleep(0.1 * (attempt + 1))

    def load_decisions(
        self,
        scope: str,
        project_id: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> List[DecisionRecord]:
        """Load decision records from audit log.

        Args:
            scope: Either "global" or "project"
            project_id: Required when scope is "project"
            since: Only load records after this timestamp (optional)

        Returns:
            List of DecisionRecord objects

        Raises:
            ValueError: If JSONL is malformed
            PermissionError: If file cannot be accessed
        """
        path = self._get_decisions_path(scope, project_id)

        if not path.exists():
            return []

        records = []

        if HAS_PORTALOCKER:
            try:
                with portalocker.Lock(path, 'r', timeout=10) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        data = json.loads(line)
                        record = DecisionRecord(**data)
                        if since is None or record.timestamp >= since:
                            records.append(record)
            except portalocker.exceptions.LockException as e:
                raise PermissionError(f"Failed to acquire lock on {path}: {e}")
        else:
            # Fallback: simple retry mechanism
            for attempt in range(3):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            data = json.loads(line)
                            record = DecisionRecord(**data)
                            if since is None or record.timestamp >= since:
                                records.append(record)
                    break
                except (IOError, OSError) as e:
                    if attempt == 2:
                        raise PermissionError(f"Failed to read {path} after 3 attempts: {e}")
                    time.sleep(0.1 * (attempt + 1))

        return records

    # === Advanced Queries ===

    def find_terms(
        self,
        scope: str,
        project_id: Optional[str] = None,
        status: Optional[str] = None,
        original_pattern: Optional[str] = None,
        include_deleted: bool = False
    ) -> List[Tuple[Term, TermMetadata]]:
        """Find terms matching criteria.

        Args:
            scope: Either "global" or "project"
            project_id: Required when scope is "project"
            status: Filter by status (optional)
            original_pattern: Filter by original text pattern (case-insensitive, optional)
            include_deleted: If False (default), exclude soft-deleted terms

        Returns:
            List of (Term, TermMetadata) tuples
        """
        terms = self.load_terms(scope, project_id)
        metadata_list = self.load_metadata(scope, project_id)

        # Build metadata lookup
        metadata_map: Dict[str, TermMetadata] = {m.term_id: m for m in metadata_list}

        results = []
        for term in terms:
            # Get metadata first
            metadata = metadata_map.get(term.id)
            if not metadata:
                continue

            # Filter by soft delete status
            if not include_deleted and metadata.is_deleted:
                continue

            # Apply status filter
            if status and term.status != status:
                continue

            # Apply pattern filter
            if original_pattern and original_pattern.lower() not in term.original.lower():
                continue

            results.append((term, metadata))

        return results

    def get_active_terms(self, project_id: Optional[str] = None) -> List[Term]:
        """Get all active terms (global + project, with project overriding global).

        Only returns terms where Term.status == "active" AND TermMetadata.is_deleted == False.

        Args:
            project_id: Project identifier (optional)

        Returns:
            List of active Term objects, with project terms overriding global terms
        """
        # Load global terms and metadata
        global_terms = self.load_terms("global")
        global_metadata_list = self.load_metadata("global")
        global_metadata_map = {m.term_id: m for m in global_metadata_list}

        # Filter global active terms (status == "active" AND not deleted)
        global_active = {}
        for t in global_terms:
            metadata = global_metadata_map.get(t.id)
            if t.status == "active" and metadata and not metadata.is_deleted:
                global_active[t.original.lower()] = t

        # Load project terms and metadata (if project_id provided)
        if project_id:
            try:
                project_terms = self.load_terms("project", project_id)
                project_metadata_list = self.load_metadata("project", project_id)
                project_metadata_map = {m.term_id: m for m in project_metadata_list}

                # Filter project active terms (status == "active" AND not deleted)
                project_active = {}
                for t in project_terms:
                    metadata = project_metadata_map.get(t.id)
                    if t.status == "active" and metadata and not metadata.is_deleted:
                        project_active[t.original.lower()] = t

                # Project terms override global terms
                result = {**global_active, **project_active}
            except (FileNotFoundError, ValueError):
                # Project glossary doesn't exist yet
                result = global_active
        else:
            result = global_active

        return list(result.values())
