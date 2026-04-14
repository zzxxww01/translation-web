"""Glossary data validation service.

This module provides comprehensive validation for glossary data integrity,
including file structure, JSON format, data consistency, and reference integrity.
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from src.services.glossary_storage import GlossaryStorage

logger = logging.getLogger(__name__)


@dataclass
class ValidationIssue:
    """Validation issue found during data integrity checks.

    Attributes:
        severity: Issue severity level ("error" or "warning")
        category: Issue category for grouping
        message: Human-readable description
        details: Additional context (optional)
    """
    severity: str  # "error", "warning"
    category: str  # "file_structure", "data_integrity", "reference"
    message: str
    details: Optional[dict] = None


@dataclass
class ValidationReport:
    """Validation report containing all issues found.

    Attributes:
        is_valid: True if no errors found (warnings are acceptable)
        issues: List of all validation issues
    """
    is_valid: bool
    issues: List[ValidationIssue]

    def summary(self) -> str:
        """Generate summary string.

        Returns:
            Summary in format "Errors: N, Warnings: M"
        """
        errors = [i for i in self.issues if i.severity == "error"]
        warnings = [i for i in self.issues if i.severity == "warning"]
        return f"Errors: {len(errors)}, Warnings: {len(warnings)}"

    def get_errors(self) -> List[ValidationIssue]:
        """Get all error-level issues.

        Returns:
            List of error issues
        """
        return [i for i in self.issues if i.severity == "error"]

    def get_warnings(self) -> List[ValidationIssue]:
        """Get all warning-level issues.

        Returns:
            List of warning issues
        """
        return [i for i in self.issues if i.severity == "warning"]


class GlossaryValidator:
    """Glossary data validator.

    Validates storage integrity including file structure, JSON format,
    data consistency, ID uniqueness, reference integrity, and soft delete
    consistency.

    Attributes:
        storage: GlossaryStorage instance to validate
    """

    def __init__(self, storage: GlossaryStorage):
        """Initialize validator.

        Args:
            storage: GlossaryStorage instance
        """
        self.storage = storage

    def validate_storage(self, scope: str, project_id: Optional[str] = None) -> ValidationReport:
        """Validate storage integrity.

        Performs comprehensive validation including:
        1. File structure existence
        2. JSON format validity
        3. Term and Metadata consistency
        4. ID uniqueness
        5. Reference integrity
        6. Soft delete consistency

        Args:
            scope: Either "global" or "project"
            project_id: Required when scope is "project"

        Returns:
            ValidationReport with all issues found
        """
        issues = []

        # 1. Check file existence
        issues.extend(self._validate_file_structure(scope, project_id))

        # 2. Check JSON format
        issues.extend(self._validate_json_format(scope, project_id))

        # 3. Check Term and Metadata consistency
        issues.extend(self._validate_data_integrity(scope, project_id))

        # 4. Check ID uniqueness
        issues.extend(self._validate_id_uniqueness(scope, project_id))

        # 5. Check reference integrity
        issues.extend(self._validate_references(scope, project_id))

        # 6. Check soft delete consistency
        issues.extend(self._validate_soft_delete_consistency(scope, project_id))

        return ValidationReport(
            is_valid=not any(i.severity == "error" for i in issues),
            issues=issues
        )

    def _validate_file_structure(self, scope: str, project_id: Optional[str]) -> List[ValidationIssue]:
        """Check file existence.

        Args:
            scope: Either "global" or "project"
            project_id: Required when scope is "project"

        Returns:
            List of validation issues
        """
        issues = []

        if scope == "global":
            required_files = [
                self.storage.base_path / "glossary" / "terms.json",
                self.storage.base_path / "glossary" / "metadata.json"
            ]
        else:
            if not project_id:
                issues.append(ValidationIssue(
                    severity="error",
                    category="file_structure",
                    message="project_id is required when scope is 'project'"
                ))
                return issues

            project_path = self.storage.base_path / "projects" / project_id / "glossary"
            required_files = [
                project_path / "terms.json",
                project_path / "metadata.json"
            ]

        for file_path in required_files:
            if not file_path.exists():
                issues.append(ValidationIssue(
                    severity="error",
                    category="file_structure",
                    message=f"Missing file: {file_path}"
                ))

        return issues

    def _validate_json_format(self, scope: str, project_id: Optional[str]) -> List[ValidationIssue]:
        """Check JSON format validity.

        Args:
            scope: Either "global" or "project"
            project_id: Required when scope is "project"

        Returns:
            List of validation issues
        """
        issues = []

        # Validate terms.json
        try:
            self.storage.load_terms(scope, project_id)
        except json.JSONDecodeError as e:
            issues.append(ValidationIssue(
                severity="error",
                category="data_integrity",
                message=f"Invalid JSON in terms.json: {e}"
            ))
        except Exception as e:
            issues.append(ValidationIssue(
                severity="error",
                category="data_integrity",
                message=f"Failed to load terms.json: {e}"
            ))

        # Validate metadata.json
        try:
            self.storage.load_metadata(scope, project_id)
        except json.JSONDecodeError as e:
            issues.append(ValidationIssue(
                severity="error",
                category="data_integrity",
                message=f"Invalid JSON in metadata.json: {e}"
            ))
        except Exception as e:
            issues.append(ValidationIssue(
                severity="error",
                category="data_integrity",
                message=f"Failed to load metadata.json: {e}"
            ))

        return issues

    def _validate_data_integrity(self, scope: str, project_id: Optional[str]) -> List[ValidationIssue]:
        """Check Term and Metadata consistency.

        Validates that:
        - Every term has corresponding metadata
        - No orphaned metadata entries exist

        Args:
            scope: Either "global" or "project"
            project_id: Required when scope is "project"

        Returns:
            List of validation issues
        """
        issues = []

        try:
            terms = self.storage.load_terms(scope, project_id)
            metadata = self.storage.load_metadata(scope, project_id)

            term_ids = {t.id for t in terms}
            metadata_term_ids = {m.term_id for m in metadata}

            # Check orphaned metadata
            orphan_metadata = metadata_term_ids - term_ids
            if orphan_metadata:
                issues.append(ValidationIssue(
                    severity="warning",
                    category="data_integrity",
                    message=f"Found {len(orphan_metadata)} metadata entries without corresponding terms",
                    details={"orphan_ids": list(orphan_metadata)[:10]}  # Show first 10
                ))

            # Check missing metadata
            missing_metadata = term_ids - metadata_term_ids
            if missing_metadata:
                issues.append(ValidationIssue(
                    severity="error",
                    category="data_integrity",
                    message=f"Found {len(missing_metadata)} terms without metadata",
                    details={"missing_ids": list(missing_metadata)[:10]}
                ))

        except Exception as e:
            issues.append(ValidationIssue(
                severity="error",
                category="data_integrity",
                message=f"Failed to validate data integrity: {e}"
            ))

        return issues

    def _validate_id_uniqueness(self, scope: str, project_id: Optional[str]) -> List[ValidationIssue]:
        """Check ID uniqueness.

        Args:
            scope: Either "global" or "project"
            project_id: Required when scope is "project"

        Returns:
            List of validation issues
        """
        issues = []

        try:
            terms = self.storage.load_terms(scope, project_id)
            term_ids = [t.id for t in terms]

            if len(term_ids) != len(set(term_ids)):
                duplicates = [tid for tid in term_ids if term_ids.count(tid) > 1]
                issues.append(ValidationIssue(
                    severity="error",
                    category="data_integrity",
                    message=f"Found duplicate term IDs",
                    details={"duplicates": list(set(duplicates))}
                ))

        except Exception as e:
            issues.append(ValidationIssue(
                severity="error",
                category="data_integrity",
                message=f"Failed to validate ID uniqueness: {e}"
            ))

        return issues

    def _validate_references(self, scope: str, project_id: Optional[str]) -> List[ValidationIssue]:
        """Check reference integrity.

        Validates that:
        - overrides_term_id references exist
        - promoted_from_term_id references exist

        Args:
            scope: Either "global" or "project"
            project_id: Required when scope is "project"

        Returns:
            List of validation issues
        """
        issues = []

        try:
            terms = self.storage.load_terms(scope, project_id)
            metadata = self.storage.load_metadata(scope, project_id)

            term_ids = {t.id for t in terms}

            for m in metadata:
                # Check overrides_term_id
                if m.overrides_term_id and m.overrides_term_id not in term_ids:
                    issues.append(ValidationIssue(
                        severity="warning",
                        category="reference",
                        message=f"Invalid overrides_term_id reference",
                        details={"term_id": m.term_id, "overrides": m.overrides_term_id}
                    ))

                # Check promoted_from_term_id
                if m.promoted_from_term_id and m.promoted_from_term_id not in term_ids:
                    issues.append(ValidationIssue(
                        severity="warning",
                        category="reference",
                        message=f"Invalid promoted_from_term_id reference",
                        details={"term_id": m.term_id, "promoted_from": m.promoted_from_term_id}
                    ))

        except Exception as e:
            issues.append(ValidationIssue(
                severity="error",
                category="reference",
                message=f"Failed to validate references: {e}"
            ))

        return issues

    def _validate_soft_delete_consistency(self, scope: str, project_id: Optional[str]) -> List[ValidationIssue]:
        """Check soft delete consistency.

        Validates that Term.status and TermMetadata.is_deleted are synchronized:
        - status="inactive" should match is_deleted=True
        - status="active" should match is_deleted=False

        Args:
            scope: Either "global" or "project"
            project_id: Required when scope is "project"

        Returns:
            List of validation issues
        """
        issues = []

        try:
            terms = self.storage.load_terms(scope, project_id)
            metadata = self.storage.load_metadata(scope, project_id)

            # Build mappings
            term_status = {t.id: t.status for t in terms}
            metadata_deleted = {m.term_id: m.is_deleted for m in metadata}

            for term_id in term_status:
                if term_id in metadata_deleted:
                    term_inactive = (term_status[term_id] == "inactive")
                    meta_deleted = metadata_deleted[term_id]

                    if term_inactive != meta_deleted:
                        issues.append(ValidationIssue(
                            severity="error",
                            category="data_integrity",
                            message=f"Soft delete inconsistency",
                            details={
                                "term_id": term_id,
                                "term_status": term_status[term_id],
                                "metadata_is_deleted": meta_deleted
                            }
                        ))

        except Exception as e:
            issues.append(ValidationIssue(
                severity="error",
                category="data_integrity",
                message=f"Failed to validate soft delete consistency: {e}"
            ))

        return issues
