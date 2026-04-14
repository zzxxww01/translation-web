#!/usr/bin/env python3
"""
Audit existing terminology data before migration.

This script analyzes the current terminology system to:
1. Count all terms (global and project-level)
2. Identify data structure patterns
3. List all terminology-related files
4. Generate migration mapping
"""

import json
import os
from pathlib import Path
from collections import defaultdict
from datetime import datetime


def audit_terminology_data(base_dir: str = "."):
    """Audit all terminology data in the project."""
    base_path = Path(base_dir)

    report = {
        "audit_time": datetime.now().isoformat(),
        "global_glossary": None,
        "project_glossaries": [],
        "total_global_terms": 0,
        "total_project_terms": 0,
        "strategy_distribution": defaultdict(int),
        "scope_distribution": defaultdict(int),
        "source_distribution": defaultdict(int),
        "status_distribution": defaultdict(int),
        "files_found": [],
        "errors": []
    }

    # Check global glossary
    global_glossary_path = base_path / "glossary" / "global_glossary_semi.json"
    if global_glossary_path.exists():
        try:
            with open(global_glossary_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                terms = data.get("terms", [])
                report["global_glossary"] = {
                    "path": str(global_glossary_path),
                    "version": data.get("version"),
                    "term_count": len(terms)
                }
                report["total_global_terms"] = len(terms)
                report["files_found"].append(str(global_glossary_path))

                # Analyze terms
                for term in terms:
                    strategy = term.get("strategy", "unknown")
                    scope = term.get("scope", "unknown")
                    source = term.get("source", "unknown")
                    status = term.get("status", "unknown")

                    report["strategy_distribution"][strategy] += 1
                    report["scope_distribution"][scope] += 1
                    report["source_distribution"][source] += 1
                    report["status_distribution"][status] += 1

        except Exception as e:
            report["errors"].append(f"Error reading global glossary: {e}")

    # Check project glossaries
    projects_dir = base_path / "projects"
    if projects_dir.exists():
        for project_dir in projects_dir.iterdir():
            if not project_dir.is_dir():
                continue

            glossary_path = project_dir / "glossary.json"
            if glossary_path.exists():
                try:
                    with open(glossary_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        terms = data.get("terms", [])

                        project_info = {
                            "project_id": project_dir.name,
                            "path": str(glossary_path),
                            "version": data.get("version"),
                            "term_count": len(terms)
                        }

                        report["project_glossaries"].append(project_info)
                        report["total_project_terms"] += len(terms)
                        report["files_found"].append(str(glossary_path))

                        # Analyze terms
                        for term in terms:
                            strategy = term.get("strategy", "unknown")
                            scope = term.get("scope", "unknown")
                            source = term.get("source", "unknown")
                            status = term.get("status", "unknown")

                            report["strategy_distribution"][strategy] += 1
                            report["scope_distribution"][scope] += 1
                            report["source_distribution"][source] += 1
                            report["status_distribution"][status] += 1

                except Exception as e:
                    report["errors"].append(f"Error reading {glossary_path}: {e}")

    # Convert defaultdicts to regular dicts for JSON serialization
    report["strategy_distribution"] = dict(report["strategy_distribution"])
    report["scope_distribution"] = dict(report["scope_distribution"])
    report["source_distribution"] = dict(report["source_distribution"])
    report["status_distribution"] = dict(report["status_distribution"])

    return report


def print_report(report: dict):
    """Print audit report in human-readable format."""
    print("=" * 80)
    print("TERMINOLOGY DATA AUDIT REPORT")
    print("=" * 80)
    print(f"\nAudit Time: {report['audit_time']}")

    print("\n--- SUMMARY ---")
    print(f"Total Global Terms: {report['total_global_terms']}")
    print(f"Total Project Terms: {report['total_project_terms']}")
    print(f"Total Terms: {report['total_global_terms'] + report['total_project_terms']}")
    print(f"Total Files: {len(report['files_found'])}")

    if report["global_glossary"]:
        print("\n--- GLOBAL GLOSSARY ---")
        print(f"Path: {report['global_glossary']['path']}")
        print(f"Version: {report['global_glossary']['version']}")
        print(f"Terms: {report['global_glossary']['term_count']}")

    print("\n--- PROJECT GLOSSARIES ---")
    print(f"Total Projects: {len(report['project_glossaries'])}")
    for proj in sorted(report['project_glossaries'], key=lambda x: x['term_count'], reverse=True):
        if proj['term_count'] > 0:
            print(f"  {proj['project_id']}: {proj['term_count']} terms (v{proj['version']})")

    print("\n--- STRATEGY DISTRIBUTION ---")
    for strategy, count in sorted(report['strategy_distribution'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {strategy}: {count}")

    print("\n--- SCOPE DISTRIBUTION ---")
    for scope, count in sorted(report['scope_distribution'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {scope}: {count}")

    print("\n--- SOURCE DISTRIBUTION ---")
    for source, count in sorted(report['source_distribution'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {source}: {count}")

    print("\n--- STATUS DISTRIBUTION ---")
    for status, count in sorted(report['status_distribution'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {status}: {count}")

    if report["errors"]:
        print("\n--- ERRORS ---")
        for error in report["errors"]:
            print(f"  {error}")

    print("\n" + "=" * 80)


def save_report(report: dict, output_path: str = "docs/migration-audit-report.json"):
    """Save audit report to JSON file."""
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\nReport saved to: {output_file}")


if __name__ == "__main__":
    report = audit_terminology_data()
    print_report(report)
    save_report(report)
