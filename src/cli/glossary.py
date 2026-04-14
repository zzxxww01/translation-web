#!/usr/bin/env python3
"""Glossary management CLI."""

import click
from pathlib import Path
from src.services.glossary_storage import GlossaryStorage


@click.group()
def cli():
    """Glossary management tool."""
    pass


@cli.command()
@click.option('--project', help='Project ID (omit to initialize global glossary)')
def init(project):
    """Initialize glossary storage structure."""
    base_path = Path.cwd()
    storage = GlossaryStorage(base_path)

    try:
        storage.initialize_storage(project)
        if project:
            click.echo(f"[OK] Project glossary initialized: {project}")
        else:
            click.echo("[OK] Global glossary initialized")
    except Exception as e:
        click.echo(f"[ERROR] Initialization failed: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--project', help='Project ID (omit to validate global glossary)')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed issue information')
def validate(project, verbose):
    """Validate glossary data integrity."""
    from src.services.glossary_validator import GlossaryValidator

    base_path = Path.cwd()
    storage = GlossaryStorage(base_path)
    validator = GlossaryValidator(storage)

    scope = "project" if project else "global"
    scope_label = f"project '{project}'" if project else "global"

    click.echo(f"Validating {scope_label} glossary...")

    try:
        report = validator.validate_storage(scope, project)

        if report.is_valid:
            click.echo(f"[OK] Validation passed: {scope_label} glossary is valid")
            if report.issues:
                click.echo(f"  {report.summary()}")
        else:
            click.echo(f"[FAIL] Validation failed: {report.summary()}")

        # Display issues
        errors = report.get_errors()
        warnings = report.get_warnings()

        if errors:
            click.echo("\nErrors:")
            for issue in errors:
                click.echo(f"  [ERROR] [{issue.category}] {issue.message}")
                if verbose and issue.details:
                    click.echo(f"     Details: {issue.details}")

        if warnings:
            click.echo("\nWarnings:")
            for issue in warnings:
                click.echo(f"  [WARN] [{issue.category}] {issue.message}")
                if verbose and issue.details:
                    click.echo(f"     Details: {issue.details}")

        # Exit with error code if validation failed
        if not report.is_valid:
            raise click.Abort()

    except Exception as e:
        click.echo(f"[ERROR] Validation failed: {e}", err=True)
        raise click.Abort()


if __name__ == '__main__':
    cli()
