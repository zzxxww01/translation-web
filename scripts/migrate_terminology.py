#!/usr/bin/env python3
"""
Migrate terminology data from old format to new format.

This script:
1. Reads old glossary files (global and project-level)
2. Converts to new Term + TermMetadata format
3. Generates deterministic UUIDs using uuid5
4. Saves to new storage structure
5. Supports dry-run mode for safety
"""

import json
import uuid
import shutil
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.terminology import Term, TermMetadata
from src.services.glossary_storage import GlossaryStorage


# UUID namespace for deterministic ID generation
TERM_NAMESPACE = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')


class TerminologyMigration:
    """Migrate terminology from old format to new format."""

    def __init__(self, base_dir: str = ".", dry_run: bool = True):
        """
        Initialize migration.

        Args:
            base_dir: Base directory of the project
            dry_run: If True, don't write any files
        """
        self.base_dir = Path(base_dir)
        self.dry_run = dry_run
        self.stats = {
            "global_terms_migrated": 0,
            "project_terms_migrated": 0,
            "total_terms": 0,
            "errors": [],
            "warnings": []
        }

    def _generate_term_id(self, scope: str, original: str, translation: Optional[str]) -> str:
        """Generate deterministic UUID for a term."""
        # Use scope:original:translation as the unique key
        key = f"{scope}:{original}:{translation or ''}"
        return str(uuid.uuid5(TERM_NAMESPACE, key))

    def _map_strategy(self, old_strategy: str) -> str:
        """Map old strategy to new strategy."""
        mapping = {
            "translate": "TRANSLATE",
            "preserve": "KEEP",
            "first_annotate": "TRANSLATE_ANNOTATE",
            "preserve_annotate": "KEEP_ANNOTATE"
        }
        return mapping.get(old_strategy, "TRANSLATE")

    def _convert_term(self, old_term: dict, scope: str, project_id: Optional[str] = None) -> Tuple[Term, TermMetadata]:
        """
        Convert old term format to new format.

        Args:
            old_term: Old term dictionary
            scope: "global" or "project"
            project_id: Project ID (required if scope is "project")

        Returns:
            Tuple of (Term, TermMetadata)
        """
        original = old_term.get("original", "")
        translation = old_term.get("translation")
        old_strategy = old_term.get("strategy", "translate")

        # Map strategy
        new_strategy = self._map_strategy(old_strategy)

        # Handle None translation: for KEEP strategies, use original as translation
        if translation is None:
            if new_strategy in ["KEEP", "KEEP_ANNOTATE"]:
                translation = original
            else:
                # For TRANSLATE strategies with no translation, use empty string
                translation = ""

        # Generate deterministic ID
        term_id = self._generate_term_id(scope, original, translation)

        # Create Term
        term = Term(
            id=term_id,
            original=original,
            translation=translation,
            strategy=new_strategy,
            source_lang="en",  # Default, could be inferred
            target_lang="zh"   # Default, could be inferred
        )

        # Parse updated_at
        updated_at_str = old_term.get("updated_at")
        if updated_at_str:
            try:
                updated_at = datetime.fromisoformat(updated_at_str.replace('Z', '+00:00'))
            except:
                updated_at = datetime.now()
        else:
            updated_at = datetime.now()

        # Determine if deleted
        status = old_term.get("status", "active")
        is_deleted = (status == "inactive")

        # Create TermMetadata
        metadata = TermMetadata(
            term_id=term_id,
            scope=scope,
            project_id=project_id,
            term_original=original,
            term_translation=translation or "",
            tags=old_term.get("tags", []),
            source=old_term.get("source", "unknown"),
            usage_count=0,
            is_deleted=is_deleted,
            created_at=updated_at,  # Use updated_at as created_at (best guess)
            updated_at=updated_at
        )

        return term, metadata

    def backup_data(self, backup_dir: str = "backups/terminology"):
        """
        Backup existing terminology data.

        Args:
            backup_dir: Directory to store backups
        """
        backup_path = self.base_dir / backup_dir
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_path / timestamp

        if self.dry_run:
            print(f"[DRY-RUN] Would backup data to: {backup_path}")
            return

        backup_path.mkdir(parents=True, exist_ok=True)

        # Backup global glossary
        global_glossary = self.base_dir / "glossary" / "global_glossary_semi.json"
        if global_glossary.exists():
            shutil.copy2(global_glossary, backup_path / "global_glossary_semi.json")
            print(f"Backed up: {global_glossary}")

        # Backup project glossaries
        projects_dir = self.base_dir / "projects"
        if projects_dir.exists():
            for project_dir in projects_dir.iterdir():
                if not project_dir.is_dir():
                    continue

                glossary_file = project_dir / "glossary.json"
                if glossary_file.exists():
                    project_backup = backup_path / "projects" / project_dir.name
                    project_backup.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(glossary_file, project_backup / "glossary.json")
                    print(f"Backed up: {glossary_file}")

        print(f"\nBackup completed: {backup_path}")
        return backup_path

    def migrate_global_glossary(self, storage: GlossaryStorage) -> int:
        """
        Migrate global glossary.

        Args:
            storage: GlossaryStorage instance

        Returns:
            Number of terms migrated
        """
        global_file = self.base_dir / "glossary" / "global_glossary_semi.json"
        if not global_file.exists():
            self.stats["warnings"].append("Global glossary file not found")
            return 0

        print(f"\nMigrating global glossary: {global_file}")

        try:
            with open(global_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            old_terms = data.get("terms", [])
            migrated_count = 0

            for old_term in old_terms:
                try:
                    term, metadata = self._convert_term(old_term, scope="global")

                    if not self.dry_run:
                        storage.add_term(term, metadata)

                    migrated_count += 1
                    if migrated_count % 10 == 0:
                        print(f"  Migrated {migrated_count}/{len(old_terms)} global terms...")

                except Exception as e:
                    error_msg = f"Error migrating global term '{old_term.get('original', 'unknown')}': {e}"
                    self.stats["errors"].append(error_msg)
                    print(f"  ERROR: {error_msg}")

            print(f"  Completed: {migrated_count} global terms migrated")
            self.stats["global_terms_migrated"] = migrated_count
            return migrated_count

        except Exception as e:
            error_msg = f"Error reading global glossary: {e}"
            self.stats["errors"].append(error_msg)
            print(f"ERROR: {error_msg}")
            return 0

    def migrate_project_glossaries(self, storage: GlossaryStorage) -> int:
        """
        Migrate all project glossaries.

        Args:
            storage: GlossaryStorage instance

        Returns:
            Number of terms migrated
        """
        projects_dir = self.base_dir / "projects"
        if not projects_dir.exists():
            self.stats["warnings"].append("Projects directory not found")
            return 0

        print(f"\nMigrating project glossaries from: {projects_dir}")

        total_migrated = 0
        project_count = 0

        for project_dir in sorted(projects_dir.iterdir()):
            if not project_dir.is_dir():
                continue

            glossary_file = project_dir / "glossary.json"
            if not glossary_file.exists():
                continue

            project_id = project_dir.name
            project_count += 1

            try:
                with open(glossary_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                old_terms = data.get("terms", [])
                if not old_terms:
                    continue

                print(f"\n  Project: {project_id} ({len(old_terms)} terms)")
                migrated_count = 0

                for old_term in old_terms:
                    try:
                        term, metadata = self._convert_term(
                            old_term,
                            scope="project",
                            project_id=project_id
                        )

                        if not self.dry_run:
                            storage.add_term(term, metadata)

                        migrated_count += 1

                    except Exception as e:
                        error_msg = f"Error migrating term '{old_term.get('original', 'unknown')}' in project '{project_id}': {e}"
                        self.stats["errors"].append(error_msg)
                        print(f"    ERROR: {error_msg}")

                print(f"    Migrated: {migrated_count} terms")
                total_migrated += migrated_count

            except Exception as e:
                error_msg = f"Error reading project glossary '{project_id}': {e}"
                self.stats["errors"].append(error_msg)
                print(f"  ERROR: {error_msg}")

        print(f"\nCompleted: {total_migrated} project terms from {project_count} projects")
        self.stats["project_terms_migrated"] = total_migrated
        return total_migrated

    def run(self, storage_path: str = "glossary_new") -> Dict:
        """
        Run the migration.

        Args:
            storage_path: Path for new storage

        Returns:
            Migration statistics
        """
        print("=" * 80)
        print("TERMINOLOGY MIGRATION")
        print("=" * 80)
        print(f"Mode: {'DRY-RUN' if self.dry_run else 'LIVE'}")
        print(f"Base directory: {self.base_dir}")
        print(f"Storage path: {storage_path}")
        print()

        # Step 1: Backup
        if not self.dry_run:
            print("Step 1: Backing up data...")
            self.backup_data()
        else:
            print("Step 1: Backup (skipped in dry-run)")

        # Step 2: Initialize storage
        print("\nStep 2: Initializing new storage...")
        storage = GlossaryStorage(str(self.base_dir / storage_path))
        print(f"  Storage initialized at: {storage.base_path}")

        # Step 3: Migrate global glossary
        print("\nStep 3: Migrating global glossary...")
        global_count = self.migrate_global_glossary(storage)

        # Step 4: Migrate project glossaries
        print("\nStep 4: Migrating project glossaries...")
        project_count = self.migrate_project_glossaries(storage)

        # Step 5: Summary
        self.stats["total_terms"] = global_count + project_count

        print("\n" + "=" * 80)
        print("MIGRATION SUMMARY")
        print("=" * 80)
        print(f"Global terms migrated: {self.stats['global_terms_migrated']}")
        print(f"Project terms migrated: {self.stats['project_terms_migrated']}")
        print(f"Total terms migrated: {self.stats['total_terms']}")
        print(f"Errors: {len(self.stats['errors'])}")
        print(f"Warnings: {len(self.stats['warnings'])}")

        if self.stats["errors"]:
            print("\nErrors:")
            for error in self.stats["errors"][:10]:  # Show first 10
                print(f"  - {error}")
            if len(self.stats["errors"]) > 10:
                print(f"  ... and {len(self.stats['errors']) - 10} more")

        if self.stats["warnings"]:
            print("\nWarnings:")
            for warning in self.stats["warnings"]:
                print(f"  - {warning}")

        print("\n" + "=" * 80)

        return self.stats


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Migrate terminology data")
    parser.add_argument("--live", action="store_true", help="Run in live mode (default is dry-run)")
    parser.add_argument("--storage-path", default="glossary_new", help="Path for new storage")
    parser.add_argument("--base-dir", default=".", help="Base directory")

    args = parser.parse_args()

    migration = TerminologyMigration(
        base_dir=args.base_dir,
        dry_run=not args.live
    )

    stats = migration.run(storage_path=args.storage_path)

    # Save stats
    stats_file = Path(args.base_dir) / "docs" / "migration-stats.json"
    stats_file.parent.mkdir(parents=True, exist_ok=True)
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    print(f"\nStatistics saved to: {stats_file}")

    # Exit with error code if there were errors
    if stats["errors"]:
        exit(1)


if __name__ == "__main__":
    main()
