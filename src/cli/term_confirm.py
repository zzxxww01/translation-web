"""
CLI interface for term confirmation workflow.

Provides interactive and batch modes for reviewing and confirming
extracted terminology candidates.
"""

import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.panel import Panel

from src.services.term_confirmation_service import (
    TermConfirmationService,
    ConfirmationAction,
    ConfirmationDecision
)
from src.services.term_conflict_detector import ConflictType


console = Console()


class TermConfirmationCLI:
    """Interactive CLI for term confirmation."""

    def __init__(self, base_path: Path):
        self.service = TermConfirmationService(base_path)

    def run_interactive(self, package_id: str, project_id: str) -> bool:
        """
        Run interactive confirmation workflow.

        Args:
            package_id: Confirmation package ID
            project_id: Project ID

        Returns:
            True if all decisions applied successfully
        """
        # Load package
        package = self.service.load_confirmation_package(package_id, project_id)
        if not package:
            console.print(f"[red]Package {package_id} not found or expired[/red]")
            return False

        console.print(Panel(
            f"[bold]Term Confirmation Package[/bold]\n"
            f"Package ID: {package_id}\n"
            f"Project: {project_id}\n"
            f"Candidates: {len(package.candidates)}\n"
            f"Conflicts: {len(package.conflicts)}",
            title="Package Info"
        ))

        # Review and apply decisions one by one
        success_count = 0
        error_count = 0

        for idx, candidate in enumerate(package.candidates):
            decision = self._review_candidate(idx, candidate, package.conflicts)
            if decision:
                try:
                    self.service.apply_decision(package_id, decision, project_id)
                    success_count += 1
                except Exception as e:
                    console.print(f"[red]Error applying decision: {e}[/red]")
                    error_count += 1

        # Summary
        console.print(f"\n[green]Applied {success_count} decisions successfully[/green]")
        if error_count > 0:
            console.print(f"[red]{error_count} errors[/red]")

        # Delete package
        self.service.delete_confirmation_package(package_id, project_id)
        return error_count == 0

    def _review_candidate(
        self,
        idx: int,
        candidate: dict,
        conflicts: list[dict]
    ) -> Optional[ConfirmationDecision]:
        """Review a single candidate and collect user decision."""
        console.print(f"\n[bold cyan]Candidate {idx + 1}[/bold cyan]")

        # Show candidate info
        table = Table(show_header=False, box=None)
        table.add_row("[bold]Term:[/bold]", candidate['original'])
        table.add_row("[bold]Translation:[/bold]", candidate['suggested_translation'])
        table.add_row("[bold]Confidence:[/bold]", f"{candidate['confidence']:.2f}")
        table.add_row("[bold]Occurrences:[/bold]", str(candidate['occurrence_count']))
        table.add_row("[bold]In Title:[/bold]", "Yes" if candidate['hit_title'] else "No")

        if candidate.get('context'):
            context = candidate['context'][:80]
            if len(candidate['context']) > 80:
                context += "..."
            table.add_row("[bold]Context:[/bold]", context)

        console.print(table)

        # Show conflicts
        candidate_conflicts = [c for c in conflicts if c.get('original') == candidate['original']]
        if candidate_conflicts:
            console.print("\n[yellow]Conflicts:[/yellow]")
            for conflict in candidate_conflicts:
                conflict_type = conflict['conflict_type']
                if conflict_type == ConflictType.TRANSLATION_MISMATCH.value:
                    console.print(
                        f"  • Translation mismatch: existing '{conflict['existing_translation']}' "
                        f"vs suggested '{conflict['suggested_translation']}'"
                    )
                elif conflict_type == ConflictType.PROJECT_OVERRIDES_GLOBAL.value:
                    console.print(
                        f"  • Project term overrides global: '{conflict['existing_translation']}'"
                    )

        # Get user decision
        console.print("\n[bold]Actions:[/bold]")
        console.print("  1. Accept")
        console.print("  2. Modify translation")
        console.print("  3. Skip")
        console.print("  4. Use existing term")
        console.print("  5. Reject")

        choice = Prompt.ask("Choose action", choices=["1", "2", "3", "4", "5"], default="1")

        if choice == "1":
            return ConfirmationDecision(
                candidate_index=idx,
                action=ConfirmationAction.ACCEPT,
                final_translation=candidate['suggested_translation']
            )
        elif choice == "2":
            new_translation = Prompt.ask("Enter new translation")
            return ConfirmationDecision(
                candidate_index=idx,
                action=ConfirmationAction.MODIFY,
                final_translation=new_translation
            )
        elif choice == "3":
            return ConfirmationDecision(
                candidate_index=idx,
                action=ConfirmationAction.SKIP
            )
        elif choice == "4":
            if candidate_conflicts:
                existing_id = candidate_conflicts[0]['existing_term_id']
                return ConfirmationDecision(
                    candidate_index=idx,
                    action=ConfirmationAction.USE_EXISTING,
                    existing_term_id=existing_id
                )
            else:
                console.print("[red]No existing term to use[/red]")
                return None
        elif choice == "5":
            return ConfirmationDecision(
                candidate_index=idx,
                action=ConfirmationAction.REJECT
            )

    def run_batch(self, package_id: str, project_id: str, accept_all: bool = False) -> bool:
        """
        Run batch confirmation (accept all or reject all).

        Args:
            package_id: Confirmation package ID
            project_id: Project ID
            accept_all: If True, accept all candidates; if False, reject all

        Returns:
            True if all decisions applied successfully
        """
        package = self.service.load_confirmation_package(package_id, project_id)
        if not package:
            console.print(f"[red]Package {package_id} not found or expired[/red]")
            return False

        action = ConfirmationAction.ACCEPT if accept_all else ConfirmationAction.REJECT
        success_count = 0
        error_count = 0

        for idx, candidate in enumerate(package.candidates):
            decision = ConfirmationDecision(
                candidate_index=idx,
                action=action,
                final_translation=candidate['suggested_translation'] if accept_all else None
            )
            try:
                self.service.apply_decision(package_id, decision, project_id)
                success_count += 1
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                error_count += 1

        console.print(f"[green]Applied {success_count}/{len(package.candidates)} decisions[/green]")

        self.service.delete_confirmation_package(package_id, project_id)
        return error_count == 0


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Term confirmation CLI")
    parser.add_argument("package_id", help="Confirmation package ID")
    parser.add_argument("project_id", help="Project ID")
    parser.add_argument("--base-path", type=Path, default=Path.cwd(), help="Base path")
    parser.add_argument("--batch", action="store_true", help="Batch mode")
    parser.add_argument("--accept-all", action="store_true", help="Accept all candidates")
    parser.add_argument("--reject-all", action="store_true", help="Reject all candidates")

    args = parser.parse_args()

    cli = TermConfirmationCLI(args.base_path)

    if args.batch:
        success = cli.run_batch(args.package_id, args.project_id, args.accept_all)
    else:
        success = cli.run_interactive(args.package_id, args.project_id)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
