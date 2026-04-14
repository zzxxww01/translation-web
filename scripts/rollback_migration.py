#!/usr/bin/env python3
"""
Rollback script for terminology migration.

This script provides a safe way to rollback the terminology migration
by restoring the old storage system and removing the new one.

Usage:
    python scripts/rollback_migration.py --dry-run  # Preview rollback
    python scripts/rollback_migration.py --execute  # Execute rollback
"""

import sys
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class MigrationRollback:
    """Handles rollback of terminology migration."""

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.old_storage_path = base_path / "glossary"
        self.new_storage_path = base_path / "glossary_new"
        self.backup_path = base_path / "glossary_backup"
        self.issues: List[str] = []
        self.warnings: List[str] = []

    def rollback(self, dry_run: bool = True) -> Dict:
        """Execute rollback process."""
        print(f"\n{'='*60}")
        print(f"Terminology Migration Rollback")
        print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
        print(f"{'='*60}\n")

        # Step 1: Verify preconditions
        print("Step 1: Verifying preconditions...")
        if not self._verify_preconditions():
            return self._generate_report(success=False)
        print("✓ Preconditions verified\n")

        # Step 2: Check if backup exists
        print("Step 2: Checking for backup...")
        has_backup = self._check_backup()
        if has_backup:
            print("✓ Backup found\n")
        else:
            print("⚠ No backup found, will keep old storage as-is\n")
            self.warnings.append("No backup found")

        # Step 3: Remove new storage
        print("Step 3: Removing new storage...")
        if not dry_run:
            self._remove_new_storage()
        print(f"{'✓ Would remove' if dry_run else '✓ Removed'} new storage\n")

        # Step 4: Restore from backup if exists
        if has_backup:
            print("Step 4: Restoring from backup...")
            if not dry_run:
                self._restore_from_backup()
            print(f"{'✓ Would restore' if dry_run else '✓ Restored'} from backup\n")

        # Step 5: Verify rollback
        print("Step 5: Verifying rollback...")
        if not dry_run:
            self._verify_rollback()
        print(f"{'✓ Would verify' if dry_run else '✓ Verified'} rollback\n")

        return self._generate_report(success=True, dry_run=dry_run)

    def _verify_preconditions(self) -> bool:
        """Verify that rollback can proceed."""
        # Check if new storage exists
        if not self.new_storage_path.exists():
            self.issues.append("New storage not found - nothing to rollback")
            return False

        # Check if old storage exists
        if not self.old_storage_path.exists():
            self.issues.append("Old storage not found - cannot rollback safely")
            return False

        return True

    def _check_backup(self) -> bool:
        """Check if backup exists."""
        return self.backup_path.exists()

    def _remove_new_storage(self):
        """Remove new storage directory."""
        if self.new_storage_path.exists():
            shutil.rmtree(self.new_storage_path)

    def _restore_from_backup(self):
        """Restore old storage from backup."""
        if self.backup_path.exists():
            # Remove current old storage
            if self.old_storage_path.exists():
                shutil.rmtree(self.old_storage_path)

            # Restore from backup
            shutil.copytree(self.backup_path, self.old_storage_path)

    def _verify_rollback(self):
        """Verify rollback was successful."""
        # Check new storage is gone
        if self.new_storage_path.exists():
            self.issues.append("New storage still exists after rollback")

        # Check old storage exists
        if not self.old_storage_path.exists():
            self.issues.append("Old storage missing after rollback")

        # Check old storage has expected files
        global_glossary = self.old_storage_path / "global_glossary.json"
        if not global_glossary.exists():
            self.issues.append("global_glossary.json missing after rollback")

    def _generate_report(self, success: bool, dry_run: bool = True) -> Dict:
        """Generate rollback report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "mode": "dry_run" if dry_run else "live",
            "success": success and len(self.issues) == 0,
            "issues": self.issues,
            "warnings": self.warnings,
            "actions": {
                "new_storage_removed": not dry_run and not self.new_storage_path.exists(),
                "backup_restored": not dry_run and self._check_backup(),
            }
        }

        # Print summary
        print(f"\n{'='*60}")
        print("Rollback Summary")
        print(f"{'='*60}")
        print(f"Status: {'SUCCESS' if report['success'] else 'FAILED'}")
        print(f"Issues: {len(self.issues)}")
        print(f"Warnings: {len(self.warnings)}")

        if self.issues:
            print("\nIssues:")
            for issue in self.issues:
                print(f"  ✗ {issue}")

        if self.warnings:
            print("\nWarnings:")
            for warning in self.warnings:
                print(f"  ⚠ {warning}")

        print(f"\n{'='*60}\n")

        return report


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Rollback terminology migration")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute rollback (default is dry-run)"
    )
    parser.add_argument(
        "--base-path",
        type=Path,
        default=Path(__file__).parent.parent,
        help="Base path for storage"
    )

    args = parser.parse_args()

    rollback = MigrationRollback(args.base_path)
    report = rollback.rollback(dry_run=not args.execute)

    # Save report
    report_path = args.base_path / "docs" / "rollback-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"Report saved to: {report_path}")

    # Exit with appropriate code
    sys.exit(0 if report["success"] else 1)


if __name__ == "__main__":
    main()
