# Interactive Fix Mode — Design

## Goal

Add `paperfmt fix --interactive` that steps through fixable diagnostics one at a time, letting the user approve or skip each fix. Non-fixable diagnostics are skipped entirely. Config management and HTML reports are deferred to the future GUI phase.

## User flow

```
$ paperfmt fix --interactive main.tex

Scanning main.tex (ieee-conf)... done.
Found 12 diagnostics (8 fixable, 4 non-fixable).

Interactive fix mode — 8 items to review.

━━━ 1/8 ━━━
  Rule: IEEE003 | Severity: warning
  Use \cite for IEEE numeric citation style.

  ── Context ──
  41 | Several approaches have been explored.
  42 | \citet{smith2020} proposed a novel method.
> 43 | \citet{jones2021} extended this work further.
  44 | Our approach builds on these foundations.
  45 | We evaluate on three benchmark datasets.
  ─────────────

  Apply? [y]es / [n]o / [s]kip rule / [a]ll / [q]uit:
```

### Actions

| Key | Action | Behavior |
|-----|--------|----------|
| `y` | Yes | Apply this rule's fix (all instances), re-run checks, drop same-rule items from queue |
| `n` | No | Skip this diagnostic, move to next |
| `s` | Skip rule | Drop all remaining diagnostics with this rule_id from queue |
| `a` | All | Apply all remaining fixes silently, print summary |
| `q` | Quit | Write current text to disk (preserving already-applied fixes), print summary |

### Edge cases

- **No fixable diagnostics**: Print "No fixable diagnostics found." and exit 0.
- **Multi-file projects**: Diagnostics from all included files (`\input`/`\include`) are shown interleaved, sorted by line. The context display includes the resolved line in the merged text.
- **`--dry-run`**: Same interactive flow, but instead of writing to disk at the end, show a unified diff.
- **Quit mid-session**: Write current text (with already-applied fixes) to disk. Remaining fixes are not applied. Message: "Quit after 3 fixes. 5 remaining."
- **Backup**: Created before the first fix, same as batch mode (`--backup`/`--no-backup` flag honored).

## Architecture

### Files modified (3 files, no new files)

**`paperfmt/cli.py`** — add `--interactive` flag to `fix_command` and the interactive loop:

```
fix_command (existing)
  ├── [new] if --interactive → _run_interactive_fix()
  │     ├── run_checks() → initial diagnostics
  │     ├── filter fixable only, sort by line
  │     ├── loop:
  │     │     ├── _show_context(text, diag) — 3 lines before/after, ">" marker
  │     │     ├── prompt y/n/s/a/q
  │     │     ├── "y" → plugin.fix(text), re-run checks, drop same-rule items
  │     │     ├── "n" → advance to next
  │     │     ├── "s" → drop all items with same rule_id
  │     │     ├── "a" → apply all remaining fixes, break
  │     │     └── "q" → write current text, return
  │     └── write final text + backup
  └── [existing] else → apply_safe_fixes() batch mode
```

**`paperfmt/core/checker.py`** — add helper:

```python
def get_fixable_rules(tex_file, template, ruleset) -> dict[str, RulePlugin]:
    """Return {rule_id: plugin} for enabled plugins that have a fix function."""
```

**`tests/test_cli.py`** — interactive mode tests using `CliRunner` with mocked stdin:
- `test_interactive_yes_applies_fix`
- `test_interactive_no_skips`
- `test_interactive_skip_rule_drops_same_rule`
- `test_interactive_all_applies_remaining`
- `test_interactive_quit_preserves_applied`
- `test_interactive_no_fixable_diagnostics`

### Key design decisions

- **Re-check after each fix**: After applying a fix, `run_checks()` runs again on the updated text to keep line numbers accurate. For ~10-20 fixable items on a typical paper, this is negligible overhead.
- **RulePlugin-level fixing**: A fix function fixes ALL instances of its rule at once. Same-rule diagnostics are dropped from the queue after applying. This matches existing fix semantics.
- **No new dependencies**: Uses `click.prompt` and string formatting already in the codebase.
- **Backup unchanged**: Standard backup logic (before first fix) applies to interactive mode too.

### Non-goals

- Config management subcommands (`paperfmt config`) — deferred to GUI phase
- HTML report (`--format html`) — deferred to GUI phase
- Per-instance (non-batch) fixes — not needed; RulePlugin-level fixing is sufficient
- Rich/colorized terminal output — stay with plain text for now
- Interactive `check` command — `--interactive` is for `fix` only

## Test strategy

All tests use `CliRunner.isolated_filesystem()` with `input=` parameter to simulate user keystrokes:

- Compliant file → "No fixable diagnostics found."
- File with one fixable issue → "y" applies fix, file is updated
- File with one fixable issue → "n" skips, file unchanged
- File with two same-rule issues → "y" fixes both at once, only one prompt shown
- File with two different-rule issues → "y" on first, "n" on second → only first fix applied
- "s" (skip rule) → drops all same-rule items, continues with other rules
- "a" (apply all) → all remaining fixes applied silently
- "q" mid-session → already-applied fixes are written, remaining skipped
- `--dry-run --interactive` → shows diff at end, no file written
- Multi-file: diagnostics from `\input`/`\include` files are included
