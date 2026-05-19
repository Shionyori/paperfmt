from __future__ import annotations

import difflib
import json
from datetime import datetime
from pathlib import Path

import click

from paperfmt import __version__
from paperfmt.core.checker import apply_safe_fixes, default_ruleset, get_fixable_rules, run_checks
from paperfmt.core.models import CheckReport, Diagnostic, RuleSet
from paperfmt.core.paperfmt_config import load_project_config
from paperfmt.core.rules import get_template_plugins
from paperfmt.core.scaffold import create_project_scaffold, supported_templates
from paperfmt.core.tex_utils import resolve_includes


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """paperfmt: a template compliance checker and safe formatter for papers."""


@main.command("init")
@click.option(
    "--template", "template_name", required=True, type=click.Choice(supported_templates()), help="Template name"
)
@click.option(
    "--out", "output_dir", default=".", type=click.Path(file_okay=False, path_type=Path), help="Output directory"
)
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


def _list_rules(template: str, ruleset: RuleSet) -> None:
    """Print all rules for the template with enabled/severity status."""
    plugins = get_template_plugins(template)
    if not plugins:
        click.echo(f"No rules defined for template '{template}'.")
        return

    click.echo(f"Rules for {template}:")
    for plugin in plugins:
        enabled = ruleset.is_enabled(plugin.rule_id)
        severity = ruleset.resolve_severity(plugin.rule_id, plugin.default_severity)
        status = "enabled " if enabled else "disabled"
        fixable = " (fixable)" if plugin.fix is not None else ""
        click.echo(f"  [{status}] {plugin.rule_id} ({severity}){fixable}")
        click.echo(f"          {plugin.description}")


def _render_text_report(report: CheckReport) -> None:
    diagnostics = report.diagnostics
    if not diagnostics:
        click.echo("No issues found.")
        return

    for item in diagnostics:
        can_fix = " (fixable)" if item.can_fix else ""
        click.echo(f"{item.severity.upper()} {item.rule_id} line {item.line}: {item.message}{can_fix}")

    fixable_count = sum(1 for d in diagnostics if d.can_fix)
    summary = f"Summary: {len(diagnostics)} issues"
    if fixable_count:
        summary += f" ({fixable_count} auto-fixable)"
    summary += f", {report.error_count} errors, {report.warning_count} warnings"
    click.echo(summary)
    if fixable_count:
        click.echo()
        click.echo(f"Hint: Run `paperfmt fix` to auto-fix {fixable_count} issue(s), or `paperfmt fix --interactive` to review each fix.")


def _build_report_file_lines(report: CheckReport) -> list[str]:
    """Build text lines for the report file from diagnostics."""
    lines: list[str] = []
    for item in report.diagnostics:
        can_fix = " (fixable)" if item.can_fix else ""
        lines.append(f"{item.severity.upper()} {item.rule_id} line {item.line}: {item.message}{can_fix}")
    if not lines:
        lines.append("No issues found.")
    fixable_count = sum(1 for d in report.diagnostics if d.can_fix)
    summary = f"Summary: {len(report.diagnostics)} issues"
    if fixable_count:
        summary += f" ({fixable_count} auto-fixable)"
    summary += f", {report.error_count} errors, {report.warning_count} warnings"
    lines.append(summary)
    if fixable_count:
        lines.append(
            f"Hint: Run `paperfmt fix` to auto-fix {fixable_count} issue(s), "
            f"or `paperfmt fix --interactive` to review each fix."
        )
    return lines


def _render_markdown_report(report: CheckReport) -> None:
    if not report.diagnostics:
        click.echo("**No issues found.**")
        return

    click.echo("## paperfmt Check Report")
    click.echo()
    click.echo(f"**Template:** {report.template}")
    click.echo(f"**File:** {report.input_file}")
    click.echo()
    click.echo("| Severity | Rule | Line | Message | Fixable |")
    click.echo("|----------|------|------|---------|---------|")
    for item in report.diagnostics:
        can_fix = "yes" if item.can_fix else "no"
        click.echo(f"| {item.severity.upper()} | {item.rule_id} | {item.line} | {item.message} | {can_fix} |")
    click.echo()
    fixable_count = sum(1 for d in report.diagnostics if d.can_fix)
    summary = (
        f"**Summary:** {len(report.diagnostics)} issues"
        + (f" ({fixable_count} auto-fixable)" if fixable_count else "")
        + f", {report.error_count} errors, {report.warning_count} warnings"
    )
    click.echo(summary)
    if fixable_count:
        click.echo()
        click.echo(
            f"> Hint: Run `paperfmt fix` to auto-fix {fixable_count} issue(s), "
            f"or `paperfmt fix --interactive` to review each fix."
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
@click.option(
    "--template", "template_name", default=None, type=click.Choice(supported_templates()), help="Template override"
)
@click.option(
    "--format", "output_format", default="text", type=click.Choice(["text", "json", "markdown"]), show_default=True
)
@click.option(
    "--list-rules",
    "list_rules",
    is_flag=True,
    default=False,
    help="List all rules for the template and exit",
)
@click.option("--strict", is_flag=True, default=False, help="Return non-zero when warnings exist")
@click.option(
    "--config",
    "config_path",
    default="paperfmt.toml",
    type=click.Path(dir_okay=False, path_type=Path),
    show_default=True,
)
def check_command(
    tex_file: Path | None,
    template_name: str | None,
    output_format: str,
    strict: bool,
    config_path: Path,
    list_rules: bool,
) -> None:
    """Scan .tex file for template compliance and formatting issues."""
    cfg = load_project_config(config_path)
    effective_template = template_name or cfg.template
    effective_tex_file = tex_file or Path(cfg.main_tex)
    state_dir = (effective_tex_file.parent.resolve() / cfg.state_dir).resolve()
    ruleset = default_ruleset(template=effective_template, bibliography=cfg.bibliography, rules=cfg.rules)

    if list_rules:
        _list_rules(effective_template, ruleset)
        return

    if not effective_tex_file.exists():
        raise click.ClickException(f"Input file not found: {effective_tex_file}")

    try:
        report = run_checks(tex_file=effective_tex_file, template=effective_template, ruleset=ruleset)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    if output_format == "json":
        fixable_count = sum(1 for d in report.diagnostics if d.can_fix)
        payload = {
            "schema_version": "1.0",
            "template": effective_template,
            "input_file": str(report.input_file),
            "summary": {
                "total": len(report.diagnostics),
                "fixable": fixable_count,
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
    elif output_format == "markdown":
        _render_markdown_report(report)
        _append_report(state_dir, "check", "\n".join(_build_report_file_lines(report)))
    else:
        _render_text_report(report)
        _append_report(state_dir, "check", "\n".join(_build_report_file_lines(report)))

    exit_code = 1 if report.error_count > 0 or (strict and report.warning_count > 0) else 0
    raise SystemExit(exit_code)


def _handle_prune_unused(tex_file: Path, cfg: object, state_dir: Path, dry_run: bool, backup: bool) -> None:
    from paperfmt.core.rules.ieee_conf import prune_unused_bib_entries

    bib_path = (tex_file.parent / cfg.bibliography).resolve()
    if not bib_path.exists():
        return

    bib_text = bib_path.read_text(encoding="utf-8")
    pruned_text, bib_changed = prune_unused_bib_entries(resolve_includes(tex_file), bib_text)
    if not bib_changed:
        return

    if dry_run:
        diff = "\n".join(
            difflib.unified_diff(
                bib_text.splitlines(),
                pruned_text.splitlines(),
                fromfile=f"{bib_path}",
                tofile=f"{bib_path} (pruned)",
                lineterm="",
            )
        )
        click.echo(diff)
        click.echo(f"Would prune unused entries from: {bib_path}")
    else:
        if backup:
            backup_dir = state_dir / "backup"
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_bib = backup_dir / f"{bib_path.name}.bak"
            backup_bib.write_text(bib_text, encoding="utf-8")
            click.echo(f"Backup created: {backup_bib}")
        bib_path.write_text(pruned_text, encoding="utf-8")
        click.echo(f"Pruned unused entries from: {bib_path}")


def _show_context(text: str, line_num: int, context_lines: int = 3) -> None:
    """Print context around a diagnostic line with a marker."""
    lines = text.splitlines()
    target_idx = line_num - 1
    start = max(0, target_idx - context_lines)
    end = min(len(lines), target_idx + context_lines + 1)

    click.echo("  ── Context ──")
    for i in range(start, end):
        marker = ">" if i == target_idx else " "
        click.echo(f"  {marker}{i + 1:3d} | {lines[i]}")
    click.echo("  ─────────────")


def _run_interactive_fix(
    tex_file: Path,
    template: str,
    ruleset: RuleSet,
    *,
    dry_run: bool,
    backup: bool,
    state_dir: Path,
) -> None:
    """Step through fixable diagnostics one at a time with user prompts."""

    # Build fixable_rules first — it is the canonical source of fixability
    # (plugin.fix is not None) matching apply_safe_fixes behaviour.
    fixable_rules = get_fixable_rules(template, ruleset)
    fixable_rule_ids = set(fixable_rules.keys())

    # Initial check
    report = run_checks(tex_file=tex_file, template=template, ruleset=ruleset)
    all_diagnostics = report.diagnostics
    # Filter by fixable_rules, not by d.can_fix, to stay consistent with
    # apply_safe_fixes.
    queue = [d for d in all_diagnostics if d.rule_id in fixable_rule_ids]

    total = len(all_diagnostics)
    fixable_count = len(queue)
    non_fixable = total - fixable_count
    click.echo(f"Found {total} diagnostics ({fixable_count} fixable, {non_fixable} non-fixable).")
    click.echo()

    if not queue:
        click.echo("No fixable diagnostics found.")
        return

    click.echo(f"Interactive fix mode — {fixable_count} items to review.")
    click.echo()

    original_text = tex_file.read_text(encoding="utf-8")
    file_text = original_text
    applied_count = 0
    skipped_count = 0
    prompt_index = 0

    # Create backup before any modifications
    if not dry_run and backup:
        backup_dir = state_dir / "backup"
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / f"{tex_file.name}.bak"
        backup_path.write_text(original_text, encoding="utf-8")
        click.echo(f"Backup created: {backup_path}")

    while queue:
        diag = queue[0]
        prompt_index += 1

        click.echo(f"━━━ {prompt_index}/{fixable_count} ━━━")
        click.echo(f"  Rule: {diag.rule_id} | Severity: {diag.severity}")
        click.echo(f"  {diag.message}")
        click.echo()

        _show_context(resolve_includes(tex_file), diag.line)

        choice = click.prompt(
            "  Apply? [y]es / [n]o / [s]kip rule / [a]ll / [q]uit",
            type=click.Choice(["y", "n", "s", "a", "q"]),
            show_choices=False,
            default="y",
        )

        if choice == "y":
            plugin = fixable_rules[diag.rule_id]  # guaranteed present by queue filter
            new_text, changed = plugin.fix(file_text)
            if changed:
                file_text = new_text
                if not dry_run:
                    tex_file.write_text(file_text, encoding="utf-8")
                applied_count += 1
                click.echo(f"  ✓ Applied fix for {diag.rule_id}.")
            else:
                click.echo(f"  - No changes needed for {diag.rule_id}.")
            # Re-check to refresh line numbers; rebuild queue from the same
            # fixable_rule_ids to stay consistent with apply_safe_fixes.
            if not dry_run:
                report = run_checks(tex_file=tex_file, template=template, ruleset=ruleset)
                queue = [d for d in report.diagnostics if d.rule_id in fixable_rule_ids]
            else:
                queue = [d for d in queue if d.rule_id != diag.rule_id]
            click.echo()

        elif choice == "n":
            queue.pop(0)
            skipped_count += 1

        elif choice == "s":
            skipped_rule = queue[0].rule_id
            removed = sum(1 for d in queue if d.rule_id == skipped_rule)
            queue = [d for d in queue if d.rule_id != skipped_rule]
            skipped_count += removed
            click.echo(f"  Skipped all '{skipped_rule}' diagnostics ({removed} items).")

        elif choice == "a":
            # Delegate to apply_safe_fixes so the result matches non-interactive fix.
            if dry_run:
                for rule_id in list(dict.fromkeys(d.rule_id for d in queue)):
                    plugin = fixable_rules.get(rule_id)
                    if plugin is not None:
                        new_text, changed = plugin.fix(file_text)
                        if changed:
                            file_text = new_text
                            applied_count += 1
            else:
                # Write current partial state so apply_safe_fixes picks it up
                tex_file.write_text(file_text, encoding="utf-8")
                result = apply_safe_fixes(tex_file=tex_file, template=template, ruleset=ruleset)
                if result.changed:
                    file_text = result.fixed_text
                    applied_count += len(result.applied_fixes)
            queue.clear()
            break

        elif choice == "q":
            remaining = len(queue)
            skipped_count += remaining
            queue.clear()
            click.echo(f"Quit after {applied_count} fixes. {remaining} remaining.")
            break

    # Write final result
    if applied_count > 0:
        diff = "\n".join(
            difflib.unified_diff(
                original_text.splitlines(),
                file_text.splitlines(),
                fromfile=str(tex_file),
                tofile=f"{tex_file} (fixed)",
                lineterm="",
            )
        )
        if dry_run:
            click.echo()
            click.echo(diff)
            click.echo(f"Dry run — would apply {applied_count} fixes, skipped {skipped_count}.")
            _append_report(state_dir, "fix(interactive-dry-run)", diff or "No diff")
        else:
            tex_file.write_text(file_text, encoding="utf-8")
            click.echo()
            click.echo(diff)
            click.echo()
            click.echo(f"Applied {applied_count} fixes, skipped {skipped_count}.")
            click.echo(f"Updated file: {tex_file}")
            _append_report(
                state_dir,
                "fix(interactive)",
                diff + "\n\n" + f"Applied {applied_count} fixes, skipped {skipped_count}.\nUpdated file: {tex_file}",
            )
    else:
        click.echo("No fixes applied.")


@main.command("fix")
@click.argument("tex_file", required=False, type=click.Path(dir_okay=False, path_type=Path))
@click.option(
    "--template", "template_name", default=None, type=click.Choice(supported_templates()), help="Template override"
)
@click.option("--dry-run", is_flag=True, default=False, help="Preview patch without writing files")
@click.option("--backup/--no-backup", default=True, show_default=True, help="Write .bak before applying fixes")
@click.option(
    "--config",
    "config_path",
    default="paperfmt.toml",
    type=click.Path(dir_okay=False, path_type=Path),
    show_default=True,
)
@click.option("--prune-unused", is_flag=True, default=False, help="Remove uncited bibliography entries")
@click.option("--interactive", "-i", is_flag=True, default=False, help="Step through fixes one at a time")
def fix_command(
    tex_file: Path | None,
    template_name: str | None,
    dry_run: bool,
    backup: bool,
    config_path: Path,
    prune_unused: bool,
    interactive: bool,
) -> None:
    """Apply safe formatting fixes that do not change paper semantics."""
    cfg = load_project_config(config_path)
    effective_template = template_name or cfg.template
    effective_tex_file = tex_file or Path(cfg.main_tex)
    state_dir = (effective_tex_file.parent.resolve() / cfg.state_dir).resolve()
    ruleset = default_ruleset(template=effective_template, bibliography=cfg.bibliography, rules=cfg.rules)

    if not effective_tex_file.exists():
        raise click.ClickException(f"Input file not found: {effective_tex_file}")

    if interactive:
        _run_interactive_fix(
            tex_file=effective_tex_file,
            template=effective_template,
            ruleset=ruleset,
            dry_run=dry_run,
            backup=backup,
            state_dir=state_dir,
        )
        if prune_unused:
            _handle_prune_unused(effective_tex_file, cfg, state_dir, dry_run=dry_run, backup=backup)
        return

    try:
        result = apply_safe_fixes(tex_file=effective_tex_file, template=effective_template, ruleset=ruleset)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    if not result.changed and not prune_unused:
        click.echo("No safe fixes needed.")
        return

    if dry_run:
        diff = ""
        if result.changed:
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
        else:
            click.echo("No safe fixes needed.")
        if prune_unused:
            _handle_prune_unused(effective_tex_file, cfg, state_dir, dry_run=True, backup=backup)
        _append_report(state_dir, "fix(dry-run)", diff or "No diff")
        return

    if result.changed:
        if backup:
            backup_dir = state_dir / "backup"
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = backup_dir / f"{effective_tex_file.name}.bak"
            backup_path.write_text(result.original_text, encoding="utf-8")
            click.echo(f"Backup created: {backup_path}")

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
        click.echo()
        click.echo(f"Applied fixes: {', '.join(sorted(set(result.applied_fixes)))}")
        click.echo(f"Updated file: {effective_tex_file}")

        effective_tex_file.write_text(result.fixed_text, encoding="utf-8")
        _append_report(
            state_dir,
            "fix",
            diff + "\n\n" + f"Applied fixes: {', '.join(sorted(set(result.applied_fixes)))}\nUpdated file: {effective_tex_file}",
        )

    if prune_unused:
        _handle_prune_unused(effective_tex_file, cfg, state_dir, dry_run=False, backup=backup)
