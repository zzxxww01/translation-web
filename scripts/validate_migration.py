#!/usr/bin/env python3
"""
Validate migrated terminology data.

This script validates:
1. File structure integrity
2. Data completeness (all terms migrated)
3. Reference integrity
4. Data format correctness
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Set
from collections import defaultdict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.glossary_storage import GlossaryStorage


class MigrationValidator:
    """Validate migrated terminology data."""

    def __init__(self, old_base_dir: str = ".", new_storage_path: str = "glossary_new"):
        """
        Initialize validator.

        Args:
            old_base_dir: Base directory with old data
            new_storage_path: Path to new storage
        """
        self.old_base_dir = Path(old_base_dir)
        self.new_storage_path = Path(old_base_dir) / new_storage_path
        self.storage = GlossaryStorage(str(self.new_storage_path))

        self.results = {
            "file_structure": {"passed": False, "issues": []},
            "data_completeness": {"passed": False, "issues": []},
            "term_counts": {"passed": False, "issues": []},
            "reference_integrity": {"passed": False, "issues": []},
            "overall_passed": False
        }

    def validate_file_structure(self) -> bool:
        """Validate that new storage structure exists and is correct."""
        print("\n1. Validating file structure...")

        issues = []

        # Check base path exists
        if not self.new_storage_path.exists():
            issues.append(f"Storage path does not exist: {self.new_storage_path}")
            self.results["file_structure"]["issues"] = issues
            return False

        # Check required directories and files
        global_glossary_dir = self.new_storage_path / "glossary"
        if not global_glossary_dir.exists():
            issues.append("Global glossary directory missing")
        else:
            # Check for terms.json and metadata.json
            if not (global_glossary_dir / "terms.json").exists():
                issues.append("Global terms.json missing")
            if not (global_glossary_dir / "metadata.json").exists():
                issues.append("Global metadata.json missing")

        projects_dir = self.new_storage_path / "projects"
        if not projects_dir.exists():
            issues.append("Projects directory missing")

        if issues:
            self.results["file_structure"]["issues"] = issues
            print(f"   FAILED: {len(issues)} issues found")
            for issue in issues:
                print(f"     - {issue}")
            return False

        print("   PASSED")
        self.results["file_structure"]["passed"] = True
        return True

    def count_old_terms(self) -> Dict[str, int]:
        """Count terms in old format."""
        counts = {"global": 0, "project": 0, "total": 0}

        # Count global terms
        global_file = self.old_base_dir / "glossary" / "global_glossary_semi.json"
        if global_file.exists():
            try:
                with open(global_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    counts["global"] = len(data.get("terms", []))
            except Exception as e:
                print(f"   Warning: Error reading global glossary: {e}")

        # Count project terms
        projects_dir = self.old_base_dir / "projects"
        if projects_dir.exists():
            for project_dir in projects_dir.iterdir():
                if not project_dir.is_dir():
                    continue

                glossary_file = project_dir / "glossary.json"
                if glossary_file.exists():
                    try:
                        with open(glossary_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            counts["project"] += len(data.get("terms", []))
                    except Exception as e:
                        print(f"   Warning: Error reading {glossary_file}: {e}")

        counts["total"] = counts["global"] + counts["project"]
        return counts

    def count_new_terms(self) -> Dict[str, int]:
        """Count terms in new format."""
        counts = {"global": 0, "project": 0, "total": 0}

        # Count global terms
        global_metadata_file = self.new_storage_path / "glossary" / "metadata.json"
        if global_metadata_file.exists():
            try:
                with open(global_metadata_file, 'r', encoding='utf-8') as f:
                    metadata_list = json.load(f)
                    counts["global"] = len(metadata_list)
            except Exception as e:
                print(f"   Warning: Error reading global metadata: {e}")

        # Count project terms
        projects_dir = self.new_storage_path / "projects"
        if projects_dir.exists():
            for project_dir in projects_dir.iterdir():
                if not project_dir.is_dir():
                    continue

                metadata_file = project_dir / "glossary" / "metadata.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata_list = json.load(f)
                            counts["project"] += len(metadata_list)
                    except Exception as e:
                        print(f"   Warning: Error reading {metadata_file}: {e}")

        counts["total"] = counts["global"] + counts["project"]
        return counts

    def validate_term_counts(self) -> bool:
        """Validate that term counts match."""
        print("\n2. Validating term counts...")

        old_counts = self.count_old_terms()
        new_counts = self.count_new_terms()

        print(f"   Old format: {old_counts['total']} terms (global: {old_counts['global']}, project: {old_counts['project']})")
        print(f"   New format: {new_counts['total']} terms (global: {new_counts['global']}, project: {new_counts['project']})")

        issues = []

        if old_counts["global"] != new_counts["global"]:
            issues.append(f"Global term count mismatch: {old_counts['global']} -> {new_counts['global']}")

        if old_counts["project"] != new_counts["project"]:
            issues.append(f"Project term count mismatch: {old_counts['project']} -> {new_counts['project']}")

        if old_counts["total"] != new_counts["total"]:
            issues.append(f"Total term count mismatch: {old_counts['total']} -> {new_counts['total']}")

        if issues:
            self.results["term_counts"]["issues"] = issues
            print(f"   FAILED: {len(issues)} issues found")
            for issue in issues:
                print(f"     - {issue}")
            return False

        print("   PASSED")
        self.results["term_counts"]["passed"] = True
        return True

    def validate_data_completeness(self) -> bool:
        """Validate that all terms have both Term and TermMetadata."""
        print("\n3. Validating data completeness...")

        issues = []

        # Check global glossary
        global_dir = self.new_storage_path / "glossary"
        if global_dir.exists():
            terms_file = global_dir / "terms.json"
            metadata_file = global_dir / "metadata.json"

            if not terms_file.exists():
                issues.append("Global terms.json missing")
            if not metadata_file.exists():
                issues.append("Global metadata.json missing")

            if terms_file.exists() and metadata_file.exists():
                try:
                    with open(terms_file, 'r', encoding='utf-8') as f:
                        terms = json.load(f)
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)

                    if len(terms) != len(metadata):
                        issues.append(f"Global term/metadata count mismatch: {len(terms)} terms vs {len(metadata)} metadata")
                except Exception as e:
                    issues.append(f"Error reading global glossary: {e}")

        # Check project glossaries
        projects_dir = self.new_storage_path / "projects"
        if projects_dir.exists():
            for project_dir in projects_dir.iterdir():
                if not project_dir.is_dir():
                    continue

                glossary_dir = project_dir / "glossary"
                if not glossary_dir.exists():
                    issues.append(f"Project {project_dir.name} missing glossary directory")
                    continue

                terms_file = glossary_dir / "terms.json"
                metadata_file = glossary_dir / "metadata.json"

                if not terms_file.exists():
                    issues.append(f"Project {project_dir.name} missing terms.json")
                if not metadata_file.exists():
                    issues.append(f"Project {project_dir.name} missing metadata.json")

                if terms_file.exists() and metadata_file.exists():
                    try:
                        with open(terms_file, 'r', encoding='utf-8') as f:
                            terms = json.load(f)
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)

                        if len(terms) != len(metadata):
                            issues.append(f"Project {project_dir.name} term/metadata count mismatch: {len(terms)} vs {len(metadata)}")
                    except Exception as e:
                        issues.append(f"Error reading project {project_dir.name}: {e}")

        if issues:
            self.results["data_completeness"]["issues"] = issues
            print(f"   FAILED: {len(issues)} issues found")
            for issue in issues[:10]:  # Show first 10
                print(f"     - {issue}")
            return False

        print("   PASSED")
        self.results["data_completeness"]["passed"] = True
        return True

    def validate_reference_integrity(self) -> bool:
        """Validate reference integrity (overrides, promotions)."""
        print("\n4. Validating reference integrity...")

        all_term_ids = set()
        references = []

        # Collect from global glossary
        global_metadata_file = self.new_storage_path / "glossary" / "metadata.json"
        if global_metadata_file.exists():
            try:
                with open(global_metadata_file, 'r', encoding='utf-8') as f:
                    metadata_list = json.load(f)
                    for metadata in metadata_list:
                        term_id = metadata.get("term_id")
                        all_term_ids.add(term_id)

                        overrides = metadata.get("overrides_term_id")
                        promoted_from = metadata.get("promoted_from_term_id")

                        if overrides:
                            references.append(("overrides", term_id, overrides))
                        if promoted_from:
                            references.append(("promoted_from", term_id, promoted_from))
            except Exception as e:
                print(f"   Warning: Error reading global metadata: {e}")

        # Collect from project glossaries
        projects_dir = self.new_storage_path / "projects"
        if projects_dir.exists():
            for project_dir in projects_dir.iterdir():
                if not project_dir.is_dir():
                    continue

                metadata_file = project_dir / "glossary" / "metadata.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata_list = json.load(f)
                            for metadata in metadata_list:
                                term_id = metadata.get("term_id")
                                all_term_ids.add(term_id)

                                overrides = metadata.get("overrides_term_id")
                                promoted_from = metadata.get("promoted_from_term_id")

                                if overrides:
                                    references.append(("overrides", term_id, overrides))
                                if promoted_from:
                                    references.append(("promoted_from", term_id, promoted_from))
                    except Exception as e:
                        print(f"   Warning: Error reading {metadata_file}: {e}")

        # Validate references
        issues = []
        for ref_type, source_id, target_id in references:
            if target_id not in all_term_ids:
                issues.append(f"Broken {ref_type} reference: {source_id} -> {target_id}")

        if issues:
            self.results["reference_integrity"]["issues"] = issues
            print(f"   FAILED: {len(issues)} broken references")
            for issue in issues[:10]:  # Show first 10
                print(f"     - {issue}")
            return False

        if references:
            print(f"   PASSED: {len(references)} references validated")
        else:
            print("   PASSED: No references to validate")
        self.results["reference_integrity"]["passed"] = True
        return True

    def run(self) -> bool:
        """Run all validations."""
        print("=" * 80)
        print("MIGRATION VALIDATION")
        print("=" * 80)
        print(f"Old data: {self.old_base_dir}")
        print(f"New storage: {self.new_storage_path}")

        # Run validations
        results = []
        results.append(self.validate_file_structure())
        results.append(self.validate_term_counts())
        results.append(self.validate_data_completeness())
        results.append(self.validate_reference_integrity())

        # Overall result
        all_passed = all(results)
        self.results["overall_passed"] = all_passed

        # Summary
        print("\n" + "=" * 80)
        print("VALIDATION SUMMARY")
        print("=" * 80)

        checks = [
            ("File Structure", self.results["file_structure"]["passed"]),
            ("Term Counts", self.results["term_counts"]["passed"]),
            ("Data Completeness", self.results["data_completeness"]["passed"]),
            ("Reference Integrity", self.results["reference_integrity"]["passed"])
        ]

        for check_name, passed in checks:
            status = "[PASSED]" if passed else "[FAILED]"
            print(f"{check_name:.<40} {status}")

        print("\n" + "=" * 80)
        if all_passed:
            print("ALL VALIDATIONS PASSED")
        else:
            print("VALIDATION FAILED")
        print("=" * 80)

        return all_passed


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate migrated terminology data")
    parser.add_argument("--old-dir", default=".", help="Base directory with old data")
    parser.add_argument("--new-storage", default="glossary_new", help="Path to new storage")
    parser.add_argument("--output", default="docs/validation-report.json", help="Output report file")

    args = parser.parse_args()

    validator = MigrationValidator(
        old_base_dir=args.old_dir,
        new_storage_path=args.new_storage
    )

    success = validator.run()

    # Save report
    output_file = Path(args.old_dir) / args.output
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(validator.results, f, indent=2, ensure_ascii=False)

    print(f"\nValidation report saved to: {output_file}")

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
