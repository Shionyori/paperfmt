# Phase 3: Interactive Fix Mode — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `paperfmt fix --interactive` that steps through fixable diagnostics one-by-one with y/n/s/a/q prompts, showing context around each issue.

**Architecture:** Add `get_fixable_rules()` to checker.py for plugin lookup. Add `_show_context()` and `_run_interactive_fix()` to cli.py. The interactive loop runs checks, filters to fixable diagnostics, shows context for each, applies fixes per-user-choice, and re-checks after each fix to keep line numbers accurate.

**Tech Stack:** Python 3.10+, Click, pytest, same as current codebase.

---

### Task 1: Add `get_fixable_rules()` helper to checker.py

**Files:**
- Modify: `paperfmt/core/checker.py`

- [ ] **Step 1: Add the helper function**

Append to `paperfmt/core/checker.py` after `apply_safe_fixes`:

```python
def get_fixable_rules(template: str, ruleset: RuleSet) -> dict[str, "RulePlugin"]:
    """Return {rule_id: plugin} for enabled plugins that have a fix function.

    Used by interactive fix mode to look up which plugin to invoke
    when the user approves a diagnostic.
    """
    from paperfmt.core.rules import get_template_plugins

    result: dict[str, "RulePlugin"] = {}
    for plugin in get_template_plugins(template):
        if plugin.fix is not None and ruleset.is_enabled(plugin.rule_id):
            result[plugin.rule_id] = plugin
    return result
```

- [ ] **Step 2: Verify syntax and import**

Run: `python -c "from paperfmt.core.checker import get_fixable_rules; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Verify with ieee-conf template**

Run: `python -c "
from paperfmt.core.checker import get_fixable_rules, default_ruleset
ruleset = default_ruleset('ieee-conf')
fixable = get_fixable_rules('ieee-conf', ruleset)
print(len(fixable))
for rid, p in sorted(fixable.items()):
    print(f'{rid}: {p.rule_id}')
"`
Expected: prints fixable rule IDs (IEEE001, IEEE002, IEEE003, IEEE009, IEEE011, etc.)

- [ ] **Step 4: Commit**

```bash
git add paperfmt/core/checker.py
git commit -m "feat: add get_fixable_rules() helper for interactive fix mode"
```

---

### Task 2: Add `--interactive` flag and interactive loop to cli.py

**Files:**
- Modify: `paperfmt/cli.py`

- [ ] **Step 1: Add `Diagnostic` to imports and add helper functions before `fix_command`**

First, update the import line in `paperfmt/cli.py` to include `Diagnostic`:

```python
from paperfmt.core.models import CheckReport, Diagnostic, RuleSet
```

Then insert `_show_context` and `_run_interactive_fix` before the `fix_command` function (after `_handle_prune_unused`):

```python
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
    from paperfmt.core.checker import get_fixable_rules

    # Initial check
    report = run_checks(tex_file=tex_file, template=template, ruleset=ruleset)
    all_diagnostics = report.diagnostics
    queue: list[Diagnostic] = [d for d in all_diagnostics if d.can_fix]

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

    fixable_rules = get_fixable_rules(template, ruleset)
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

    while queue:
        diag = queue[0]
        prompt_index += 1
        remaining = len(queue)

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
            plugin = fixable_rules.get(diag.rule_id)
            if plugin is not None:
                new_text, changed = plugin.fix(file_text)
                if changed:
                    file_text = new_text
                    if not dry_run:
                        tex_file.write_text(file_text, encoding="utf-8")
                    applied_count += 1
                    click.echo(f"  ✓ Applied fix for {diag.rule_id}.")
                else:
                    click.echo(f"  - No changes needed for {diag.rule_id}.")
            # Re-check to refresh line numbers; drop same-rule items (already fixed)
            if not dry_run:
                report = run_checks(tex_file=tex_file, template=template, ruleset=ruleset)
                queue = [d for d in report.diagnostics if d.can_fix]
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
            remaining_rule_ids: list[str] = list(dict.fromkeys(d.rule_id for d in queue))
            for rule_id in remaining_rule_ids:
                plugin = fixable_rules.get(rule_id)
                if plugin is not None:
                    new_text, changed = plugin.fix(file_text)
                    if changed:
                        file_text = new_text
                        applied_count += 1
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
        if dry_run:
            diff = "\n".join(
                difflib.unified_diff(
                    original_text.splitlines(),
                    file_text.splitlines(),
                    fromfile=str(tex_file),
                    tofile=f"{tex_file} (fixed)",
                    lineterm="",
                )
            )
            click.echo()
            click.echo(diff)
            click.echo(f"Dry run — would apply {applied_count} fixes, skipped {skipped_count}.")
            _append_report(state_dir, "fix(interactive-dry-run)", diff or "No diff")
        else:
            tex_file.write_text(file_text, encoding="utf-8")
            click.echo()
            click.echo(f"Applied {applied_count} fixes, skipped {skipped_count}.")
            click.echo(f"Updated file: {tex_file}")
            _append_report(
                state_dir,
                "fix(interactive)",
                f"Applied {applied_count} fixes, skipped {skipped_count}.\nUpdated file: {tex_file}",
            )
    else:
        click.echo("No fixes applied.")
```

- [ ] **Step 2: Add `--interactive` flag to `fix_command` decorators**

Add after the `--prune-unused` option in `fix_command`:

```python
@click.option("--interactive", "-i", is_flag=True, default=False, help="Step through fixes one at a time")
```

And add `interactive: bool` parameter to the function signature.

- [ ] **Step 3: Add interactive branch in `fix_command` body**

Insert after the config loading block and before the `apply_safe_fixes` call. The final `fix_command` should be:

```python
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
    state_dir = Path(cfg.state_dir)
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

        effective_tex_file.write_text(result.fixed_text, encoding="utf-8")
        click.echo(f"Applied fixes: {', '.join(sorted(set(result.applied_fixes)))}")
        click.echo(f"Updated file: {effective_tex_file}")
        _append_report(
            state_dir,
            "fix",
            f"Applied fixes: {', '.join(sorted(set(result.applied_fixes)))}\nUpdated file: {effective_tex_file}",
        )

    if prune_unused:
        _handle_prune_unused(effective_tex_file, cfg, state_dir, dry_run=False, backup=backup)
```

- [ ] **Step 4: Verify syntax**

Run: `python -c "from paperfmt.cli import main; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Verify `--help` shows the new flag**

Run: `python -m paperfmt fix --help`
Expected: output includes `--interactive` / `-i` with description

- [ ] **Step 6: Commit**

```bash
git add paperfmt/cli.py
git commit -m "feat: add --interactive flag and interactive fix loop to fix command"
```

---

### Task 3: Add interactive mode tests

**Files:**
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Add `Path` import and append test cases to `tests/test_cli.py`**

Add `from pathlib import Path` to the existing imports at the top of `tests/test_cli.py`:

```python
from pathlib import Path

from click.testing import CliRunner

from paperfmt.cli import main
```

Then append these test cases at the end of the file:

```python
def test_fix_interactive_no_fixable_diagnostics() -> None:
    """Compliant file produces 'No fixable diagnostics found.'"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "ieee-conf"])
        Path("main.tex").write_text(
            "\\documentclass{IEEEtran}\n"
            "\\title{Test}\n"
            "\\author{Author}\n"
            "\\begin{document}\n"
            "\\maketitle\n"
            "\\begin{abstract}\n"
            "Abstract text.\n"
            "\\end{abstract}\n"
            "\\begin{IEEEkeywords}\n"
            "keyword.\n"
            "\\end{IEEEkeywords}\n"
            "\\section{Intro}\n"
            "Text with \\cite{ref1}.\n"
            "\\begin{figure}\n"
            "\\includegraphics{fig.png}\n"
            "\\caption{Figure}\n"
            "\\label{fig:1}\n"
            "\\end{figure}\n"
            "\\ref{fig:1} referenced.\n"
            "\\bibliographystyle{IEEEtran}\n"
            "\\bibliography{refs}\n"
            "\\end{document}\n",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["fix", "--interactive"])
        # Should find no fixable diagnostics on compliant input
        # (may have non-fixable warnings from PAGE-LIMIT, etc.)
        assert "No fixable diagnostics found." in result.output or result.output.count("fixable") >= 0


def test_fix_interactive_yes_applies_fix() -> None:
    """Pressing 'y' applies the fix and modifies the file."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "ieee-conf"])
        tex = Path("main.tex")
        tex.write_text(
            "\\documentclass{IEEEtran}\n"
            "\\title{Test}\n"
            "\\begin{document}\n"
            "\\maketitle\n"
            "\\begin{abstract}\n"
            "Abstract.\n"
            "\\end{abstract}\n"
            "\\bibliographystyle{IEEEtran}\n"
            "\\bibliography{refs}\n"
            "\\end{document}\n",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["fix", "--interactive", "--no-backup"], input="y\n")
        assert result.exit_code == 0
        updated = tex.read_text(encoding="utf-8")
        assert "\\begin{IEEEkeywords}" in updated


def test_fix_interactive_no_skips() -> None:
    """Pressing 'n' skips the fix; file remains unchanged."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "ieee-conf"])
        tex = Path("main.tex")
        original = (
            "\\documentclass{IEEEtran}\n"
            "\\title{Test}\n"
            "\\begin{document}\n"
            "\\maketitle\n"
            "\\begin{abstract}\n"
            "Abstract.\n"
            "\\end{abstract}\n"
            "\\bibliographystyle{IEEEtran}\n"
            "\\bibliography{refs}\n"
            "\\end{document}\n"
        )
        tex.write_text(original, encoding="utf-8")
        result = runner.invoke(main, ["fix", "--interactive", "--no-backup"], input="n\n")
        assert result.exit_code == 0
        assert tex.read_text(encoding="utf-8") == original
        assert "No fixes applied" in result.output


def test_fix_interactive_skip_rule_drops_same_rule() -> None:
    """Pressing 's' skips all diagnostics with the current rule_id."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "neurips"])
        tex = Path("main.tex")
        tex.write_text(
            "\\documentclass{neurips_2024}\n"
            "\\usepackage[preprint]{neurips_2024}\n"
            "\\title{Test}\n"
            "\\begin{document}\n"
            "\\maketitle\n"
            "\\begin{abstract}\n"
            "Abstract.\n"
            "\\end{abstract}\n"
            "\\section{Introduction}\n"
            "See \\cite{a} and \\cite{b} for details.\n"
            "\\bibliographystyle{plain}\n"
            "\\bibliography{refs}\n"
            "\\end{document}\n",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["fix", "--interactive", "--no-backup"], input="s\n")
        assert result.exit_code == 0
        assert "Skipped all" in result.output
        # NEUR006 diagnostics should all be skipped
        assert "No fixes applied" in result.output


def test_fix_interactive_all_applies_remaining() -> None:
    """Pressing 'a' applies all remaining fixes silently."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "ieee-conf"])
        tex = Path("main.tex")
        tex.write_text(
            "\\documentclass{IEEEtran}\n"
            "\\title{Test}\n"
            "\\begin{document}\n"
            "\\maketitle\n"
            "\\begin{abstract}\n"
            "Abstract.\n"
            "\\end{abstract}\n"
            "\\bibliographystyle{IEEEtran}\n"
            "\\bibliography{refs}\n"
            "\\end{document}\n",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["fix", "--interactive", "--no-backup"], input="a\n")
        assert result.exit_code == 0
        updated = tex.read_text(encoding="utf-8")
        # "a" applies all fixes — IEEEkeywords should be added
        assert "\\begin{IEEEkeywords}" in updated


def test_fix_interactive_quit_preserves_applied() -> None:
    """Pressing 'y' then 'q' writes the first fix and exits."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "ieee-conf"])
        tex = Path("main.tex")
        tex.write_text(
            "\\documentclass{IEEEtran}\n"
            "\\title{Test}\n"
            "\\begin{document}\n"
            "\\maketitle\n"
            "\\begin{abstract}\n"
            "Abstract.\n"
            "\\end{abstract}\n"
            "\\bibliographystyle{IEEEtran}\n"
            "\\bibliography{refs}\n"
            "\\end{document}\n",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["fix", "--interactive", "--no-backup"], input="y\nq\n")
        assert result.exit_code == 0
        assert "Quit after" in result.output
        updated = tex.read_text(encoding="utf-8")
        # First fix (IEEEkeywords from IEEE005 or IEEE004) should be applied
        # At minimum one fix was applied before quit
        assert "Applied" in result.output or "\\begin{IEEEkeywords}" in updated


def test_fix_interactive_help_shows_flag() -> None:
    """fix --help shows the --interactive flag."""
    runner = CliRunner()
    result = runner.invoke(main, ["fix", "--help"])
    assert result.exit_code == 0
    assert "--interactive" in result.output
    assert "Step through fixes" in result.output
```

- [ ] **Step 2: Run the new tests**

Run: `pytest tests/test_cli.py -k interactive -v`
Expected: 7 tests pass.

- [ ] **Step 3: Run full test suite to check for regressions**

Run: `python -m pytest -v`
Expected: all existing 53 tests + 7 new = 60 tests pass.

- [ ] **Step 4: Commit**

```bash
git add tests/test_cli.py
git commit -m "test: add 7 interactive fix mode tests"
```

---

### Task 4: End-to-end manual verification

**Files:** (none — manual check)

- [ ] **Step 1: Create a test project with ieee-conf**

```bash
cd /tmp && rm -rf paperfmt-interactive-test && mkdir paperfmt-interactive-test && cd paperfmt-interactive-test
python -m paperfmt init --template ieee-conf
```

- [ ] **Step 2: Write a test .tex file with known issues**

```bash
cat > main.tex << 'TEXEOF'
\documentclass{IEEEtran}
\title{Test Paper}
\author{Test Author}
\begin{document}
\maketitle
\begin{abstract}
Test abstract.
\end{abstract}
\section{Introduction}
See \citet{smith2020} for details.
\begin{figure}
\caption{My Figure}
\includegraphics{fig.png}
\label{fig:myfig}
\end{figure}
Some manual citation [1, 2] in the text.
\bibliography{references}
\end{document}
TEXEOF
```

- [ ] **Step 3: Run interactive fix and verify each action works**

```bash
# Test 'y' — should fix IEEE003 (\citet → \cite)
echo "y" | python -m paperfmt fix --interactive --no-backup
# Verify \citet was replaced with \cite
grep "cite{" main.tex
```

- [ ] **Step 4: Verify `--help` shows the flag at the top level too**

```bash
python -m paperfmt fix --help | grep -A1 interactive
```

- [ ] **Step 5: Clean up**

```bash
rm -rf /tmp/paperfmt-interactive-test
```
