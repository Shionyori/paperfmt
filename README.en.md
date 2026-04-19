[简体中文](./README.md) | English

# paperfmt

paperfmt is a CLI tool for pre-submission paper quality checks.

Current stable template: `ieee-conf`.

## Commands

```bash
paperfmt init --template ieee-conf [--out DIR] [--force]
paperfmt check [INPUT.tex] [--template ieee-conf] [--config paperfmt.toml] [--format text|json] [--strict]
paperfmt fix [INPUT.tex] [--template ieee-conf] [--config paperfmt.toml] [--dry-run] [--backup/--no-backup]
```

Notes:
- `init` bootstraps tool files (`paperfmt.toml` and `.paperfmt/`).
- `check` / `fix` read `main_tex`, `bibliography`, and `rules` from `paperfmt.toml` by default.
- Execution records are appended to `.paperfmt/report.txt`.

## Configuration-Driven Flow

`paperfmt.toml` is plain text and drives the pipeline:

`paperfmt.toml -> RuleSet -> template rules plugins`

Typical editable keys:
- `main_tex`
- `bibliography`
- `state_dir`
- per-rule `enabled` / `severity`

## Implemented Rules (ieee-conf)

- `IEEE001` figure caption order (`\caption` should be after `\includegraphics`)
- `IEEE002` table caption order (`\caption` should be before `tabular`)
- `IEEE003` citation style normalization recommendation (`\citep` / `\citet`)
- `IEEE004` missing `abstract` environment
- `IEEE005` missing `IEEEkeywords` environment
- `IEEE006` anonymization leak in author block
- `IEEE007` missing DOI for cited bibliography entries
- `CITE-MANUAL` manual numeric citations (e.g. `[1]`)
- `REF-HARDCODE` hardcoded cross-references (e.g. `Eq. (1)`)
- `TAB-FORMAT` `\hline` style in tables (booktabs recommended)
- `BIB-CROSSCHECK` `.tex` and `.bib` cross-check (missing keys / unused entries)

## Implemented Safe Fixes

- fix figure caption order (`IEEE001`)
- fix table caption order (`IEEE002`)
- normalize `\citep` / `\citet` to `\cite` (`IEEE003`)

## Rule Extensibility

Rules are organized per template:

- `paperfmt/core/rules/ieee_conf.py`: all `ieee-conf` rules
- `paperfmt/core/rules/__init__.py`: template-to-rule-set registry

To add a new template:
1. Create `paperfmt/core/rules/<template>.py`
2. Register it in `paperfmt/core/rules/__init__.py`
3. Add template identity in `paperfmt/core/registry.py`
