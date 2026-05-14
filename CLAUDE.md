# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Development install (editable, with test deps)
pip install -e ".[dev]"

# Run all tests
python -m pytest -q

# Run tests with verbose output
python -m pytest -v

# Run a specific test file
python -m pytest tests/test_workflow.py

# Run the CLI during development
python -m paperfmt --help

# Build distribution packages
python -m build
```

## Architecture

paperfmt is a CLI tool for pre-submission quality checks on academic paper `.tex` files. It has three commands: `init`, `check`, `fix`. The only stable template is `ieee-conf`.

### Package structure

```
paperfmt/
├── cli.py              # Click CLI: init, check, fix commands
├── __init__.py         # Version only (__version__)
├── __main__.py         # python -m paperfmt entry
└── core/
    ├── models.py       # Dataclasses: Diagnostic, CheckReport, FixReport, RuleSet, RuleOverride
    ├── checker.py      # run_checks() and apply_safe_fixes() — iterates RulePlugins
    ├── rules/
    │   ├── base.py     # RulePlugin dataclass: rule_id, default_severity, check fn, optional fix fn
    │   ├── ieee_conf.py # All ieee-conf rule implementations (IEEE001-IEEE007 + CITE-MANUAL, etc.)
    │   └── __init__.py # TEMPLATE_RULES dict mapping template name → tuple of RulePlugins
    ├── registry.py     # Template name canonicalization (normalize_template, supported_templates)
    ├── paperfmt_config.py # Reads/writes paperfmt.toml (config-driven rule enable/severity)
    └── scaffold.py     # init command: creates .paperfmt/ dir, paperfmt.toml, backups
```

### Rule plugin system

Each rule is a `RulePlugin` instance with:
- `rule_id` — unique string identifier (e.g. `IEEE001`)
- `default_severity` — `"error"` or `"warning"`
- `check(text, tex_file, ruleset)` — returns `list[Diagnostic]`
- `fix(text)` — optional, returns `(new_text, changed_bool)`

Rules for a template are collected as a `tuple[RulePlugin, ...]` and registered in `TEMPLATE_RULES` dict in `paperfmt/core/rules/__init__.py`. `checker.py` iterates plugins, honoring per-rule `enabled`/`severity` overrides from `RuleSet`.

### Configuration flow

`paperfmt.toml` → `load_project_config()` → `ProjectConfig` → `RuleSet` with per-rule overrides → `run_checks()` / `apply_safe_fixes()` iterates enabled rules.

Users manually edit `paperfmt.toml` to toggle rules or change severity. If the config file is missing, all rules run with their factory defaults.

### Adding a new template

1. Create `paperfmt/core/rules/<template>.py` with a `RULES` tuple of `RulePlugin` instances
2. Import and register it in `paperfmt/core/rules/__init__.py` `TEMPLATE_RULES` dict
3. Add the template identifier to `CANONICAL_TEMPLATES` in `paperfmt/core/registry.py`

### Key constraints

- **Safe fixes only**: `fix` commands must not change paper semantics — only cosmetic/formatting changes like caption reordering, citation normalization
- **All fixes create backups** by default (`.paperfmt/backup/`), written before applying changes
- **`--dry-run`** outputs a unified diff without modifying files
- **`--strict`** mode returns exit code 1 when warnings exist (for CI use)
