from __future__ import annotations

import difflib
import json
from pathlib import Path

import click

from paperfmt import __version__
from paperfmt.core.checker import apply_safe_fixes, run_checks
from paperfmt.core.scaffold import create_project_scaffold, supported_templates


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """paperfmt: a template compliance checker and safe formatter for papers."""


@main.command("init")
@click.option("--template", "template_name", required=True, type=click.Choice(supported_templates()), help="Template name")
@click.option("--out", "output_dir", default=".", type=click.Path(file_okay=False, path_type=Path), help="Output directory")
@click.option("--force", is_flag=True, default=False, help="Overwrite existing files")
def init_command(template_name: str, output_dir: Path, force: bool) -> None:
    """Initialize a starter project for a paper template."""
    try:
        created_files = create_project_scaffold(template=template_name, output_dir=output_dir, force=force)
    except (ValueError, FileExistsError) as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"Initialized template '{template_name}' in {output_dir.resolve()}")
    for path in created_files:
        click.echo(f"- created: {path}")


def _render_text_report(report: object) -> None:
    diagnostics = getattr(report, "diagnostics")
    if not diagnostics:
        click.echo("No issues found.")
        return

    for item in diagnostics:
        can_fix = " (fixable)" if item.can_fix else ""
        click.echo(f"{item.severity.upper()} {item.rule_id} line {item.line}: {item.message}{can_fix}")

    click.echo(
        f"Summary: {len(diagnostics)} issues, "
        f"{report.error_count} errors, {report.warning_count} warnings"
    )


@main.command("check")
@click.argument("tex_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--template", "template_name", default="ieee", type=click.Choice(supported_templates()), show_default=True)
@click.option("--format", "output_format", default="text", type=click.Choice(["text", "json"]), show_default=True)
@click.option("--strict", is_flag=True, default=False, help="Return non-zero when warnings exist")
def check_command(tex_file: Path, template_name: str, output_format: str, strict: bool) -> None:
    """Scan .tex file for template compliance and formatting issues."""
    try:
        report = run_checks(tex_file=tex_file, template=template_name)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    if output_format == "json":
        payload = {
            "input_file": str(report.input_file),
            "summary": {
                "total": len(report.diagnostics),
                "errors": report.error_count,
                "warnings": report.warning_count,
            },
            "diagnostics": [
                {
                    "rule_id": d.rule_id,
                    "severity": d.severity,
                    "message": d.message,
                    "line": d.line,
                    "can_fix": d.can_fix,
                }
                for d in report.diagnostics
            ],
        }
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        _render_text_report(report)

    exit_code = 1 if report.error_count > 0 or (strict and report.warning_count > 0) else 0
    raise SystemExit(exit_code)


@main.command("fix")
@click.argument("tex_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--template", "template_name", default="ieee", type=click.Choice(supported_templates()), show_default=True)
@click.option("--dry-run", is_flag=True, default=False, help="Preview patch without writing files")
@click.option("--backup/--no-backup", default=True, show_default=True, help="Write .bak before applying fixes")
def fix_command(tex_file: Path, template_name: str, dry_run: bool, backup: bool) -> None:
    """Apply safe formatting fixes that do not change paper semantics."""
    try:
        result = apply_safe_fixes(tex_file=tex_file, template=template_name)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    if not result.changed:
        click.echo("No safe fixes needed.")
        return

    if dry_run:
        diff = "\n".join(
            difflib.unified_diff(
                result.original_text.splitlines(),
                result.fixed_text.splitlines(),
                fromfile=f"{tex_file}",
                tofile=f"{tex_file} (fixed)",
                lineterm="",
            )
        )
        click.echo(diff)
        click.echo(f"Dry run only. Planned fixes: {', '.join(sorted(set(result.applied_fixes)))}")
        return

    if backup:
        backup_path = tex_file.with_suffix(tex_file.suffix + ".bak")
        backup_path.write_text(result.original_text, encoding="utf-8")
        click.echo(f"Backup created: {backup_path}")

    tex_file.write_text(result.fixed_text, encoding="utf-8")
    click.echo(f"Applied fixes: {', '.join(sorted(set(result.applied_fixes)))}")
    click.echo(f"Updated file: {tex_file}")
