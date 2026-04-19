from __future__ import annotations

import difflib
from datetime import datetime
import json
from pathlib import Path

import click

from paperfmt import __version__
from paperfmt.core.checker import apply_safe_fixes, default_ruleset, run_checks
from paperfmt.core.project_config import load_project_config
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
    """Initialize paperfmt state and config for an existing paper project."""
    try:
        created_files = create_project_scaffold(
            template=template_name,
            output_dir=output_dir,
            force=force,
        )
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


def _append_report(state_dir: Path, title: str, body: str) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    report_path = state_dir / "report.txt"
    timestamp = datetime.now().isoformat(timespec="seconds")
    with report_path.open("a", encoding="utf-8") as fh:
        fh.write(f"[{timestamp}] {title}\n")
        fh.write(body.rstrip() + "\n\n")


@main.command("check")
@click.argument("tex_file", required=False, type=click.Path(dir_okay=False, path_type=Path))
@click.option("--template", "template_name", default=None, type=click.Choice(supported_templates()), help="Template override")
@click.option("--format", "output_format", default="text", type=click.Choice(["text", "json"]), show_default=True)
@click.option("--strict", is_flag=True, default=False, help="Return non-zero when warnings exist")
@click.option("--config", "config_path", default="paperfmt.toml", type=click.Path(dir_okay=False, path_type=Path), show_default=True)
def check_command(tex_file: Path | None, template_name: str | None, output_format: str, strict: bool, config_path: Path) -> None:
    """Scan .tex file for template compliance and formatting issues."""
    cfg = load_project_config(config_path)
    effective_template = template_name or cfg.template
    effective_tex_file = tex_file or Path(cfg.main_tex)
    state_dir = Path(cfg.state_dir)
    ruleset = default_ruleset(template=effective_template, bibliography=cfg.bibliography, rules=cfg.rules)

    if not effective_tex_file.exists():
        raise click.ClickException(f"Input file not found: {effective_tex_file}")

    try:
        report = run_checks(tex_file=effective_tex_file, template=effective_template, ruleset=ruleset)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    if output_format == "json":
        payload = {
            "schema_version": "1.0",
            "template": effective_template,
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
        rendered = json.dumps(payload, ensure_ascii=False, indent=2)
        click.echo(rendered)
        _append_report(state_dir, "check", rendered)
    else:
        lines: list[str] = []
        _render_text_report(report)
        for item in report.diagnostics:
            can_fix = " (fixable)" if item.can_fix else ""
            lines.append(f"{item.severity.upper()} {item.rule_id} line {item.line}: {item.message}{can_fix}")
        if not lines:
            lines.append("No issues found.")
        lines.append(f"Summary: {len(report.diagnostics)} issues, {report.error_count} errors, {report.warning_count} warnings")
        _append_report(state_dir, "check", "\n".join(lines))

    exit_code = 1 if report.error_count > 0 or (strict and report.warning_count > 0) else 0
    raise SystemExit(exit_code)


@main.command("fix")
@click.argument("tex_file", required=False, type=click.Path(dir_okay=False, path_type=Path))
@click.option("--template", "template_name", default=None, type=click.Choice(supported_templates()), help="Template override")
@click.option("--dry-run", is_flag=True, default=False, help="Preview patch without writing files")
@click.option("--backup/--no-backup", default=True, show_default=True, help="Write .bak before applying fixes")
@click.option("--config", "config_path", default="paperfmt.toml", type=click.Path(dir_okay=False, path_type=Path), show_default=True)
def fix_command(tex_file: Path | None, template_name: str | None, dry_run: bool, backup: bool, config_path: Path) -> None:
    """Apply safe formatting fixes that do not change paper semantics."""
    cfg = load_project_config(config_path)
    effective_template = template_name or cfg.template
    effective_tex_file = tex_file or Path(cfg.main_tex)
    state_dir = Path(cfg.state_dir)
    ruleset = default_ruleset(template=effective_template, bibliography=cfg.bibliography, rules=cfg.rules)

    if not effective_tex_file.exists():
        raise click.ClickException(f"Input file not found: {effective_tex_file}")

    try:
        result = apply_safe_fixes(tex_file=effective_tex_file, template=effective_template, ruleset=ruleset)
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
                fromfile=f"{effective_tex_file}",
                tofile=f"{effective_tex_file} (fixed)",
                lineterm="",
            )
        )
        click.echo(diff)
        click.echo(f"Dry run only. Planned fixes: {', '.join(sorted(set(result.applied_fixes)))}")
        _append_report(state_dir, "fix(dry-run)", diff or "No diff")
        return

    if backup:
        backup_dir = state_dir / "backup"
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / f"{effective_tex_file.name}.bak"
        backup_path.write_text(result.original_text, encoding="utf-8")
        click.echo(f"Backup created: {backup_path}")

    effective_tex_file.write_text(result.fixed_text, encoding="utf-8")
    click.echo(f"Applied fixes: {', '.join(sorted(set(result.applied_fixes)))}")
    click.echo(f"Updated file: {effective_tex_file}")
    _append_report(
        state_dir,
        "fix",
        f"Applied fixes: {', '.join(sorted(set(result.applied_fixes)))}\nUpdated file: {effective_tex_file}",
    )
