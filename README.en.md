[简体中文](./README.md) | English

# paperfmt

paperfmt is a CLI tool for pre-submission paper quality checks. It supports multi-file `.tex` projects, markdown reports, and automatic safe fixes.

Current stable templates: `ieee-conf`, `acm-conf`, `neurips`, `acl-conf` (23 rules each, 11 shared rules).

## Installation

```bash
pip install -e ".[dev]"         # development install (with test dependencies)
pip install -e ".[image,link]"   # optional: image resolution and link validation
pip install -e ".[full]"         # all optional dependencies
```

## Commands

```bash
# Initialize a project
paperfmt init --template ieee-conf [--out DIR] [--force]

# Check
paperfmt check [INPUT.tex] \
    [--template ieee-conf] \
    [--config paperfmt.toml] \
    [--format text|json|markdown] \
    [--list-rules] \
    [--strict]

# Fix
paperfmt fix [INPUT.tex] \
    [--template ieee-conf] \
    [--config paperfmt.toml] \
    [--dry-run] \
    [--backup/--no-backup] \
    [--prune-unused] \
    [--interactive]
```

Notes:
- `init` bootstraps tool files (`paperfmt.toml` and `.paperfmt/`). Existing `.tex` files are automatically backed up to `.paperfmt/backup/`.
- `check` / `fix` read `main_tex`, `bibliography`, and `rules` from `paperfmt.toml` by default.
- `check` recursively resolves `\input`/`\include` directives across files.
- `--format markdown` outputs a markdown table report.
- `--list-rules` lists all template rules with their enabled status and severity.
- `--prune-unused` removes uncited entries from `.bib` files.
- `--interactive` / `-i` steps through fixes one at a time with context display and `[y]es/[n]o/[s]kip rule/[a]ll/[q]uit` prompts.
- Execution records are appended to `.paperfmt/report.txt`.

## Configuration-Driven Flow

`paperfmt.toml` is plain text and drives the pipeline:

`paperfmt.toml -> RuleSet -> template rules plugins`

Typical editable keys:
- `main_tex`
- `bibliography`
- `state_dir`
- per-rule `enabled` / `severity`

## Implemented Rules (ieee-conf, 23 total)

### Structure & Layout
- `IEEE001` figure caption order (`\caption` should be after `\includegraphics`) **[fixable]**
- `IEEE002` table caption order (`\caption` should be before `tabular`) **[fixable]**
- `IEEE004` missing `abstract` environment (error)
- `IEEE005` missing `IEEEkeywords` environment
- `IEEE008` missing `\thanks` for author affiliations/funding
- `IEEE011` missing `\bibliographystyle{IEEEtran}` (error) **[fixable]**
- `IEEE012` missing column balancing command (`\balance`, etc.)
- `TAB-FORMAT` `\hline` style in tables (booktabs recommended)

### Citations & Cross-References
- `IEEE003` citation style normalization (`\citep` / `\citet` → `\cite`) **[fixable]**
- `IEEE009` `\cite` keys should be comma-separated **[fixable]**
- `IEEE010` equation environment missing trailing punctuation
- `CITE-MANUAL` manual numeric citations (e.g. `[1]`)
- `REF-HARDCODE` hardcoded cross-references (e.g. `Eq. (1)`)
- `FIG-REF` figure label not referenced in text
- `TAB-REF` table label not referenced in text
- `EQ-REF` equation label not referenced in text

### Anonymization & Bibliography
- `IEEE006` anonymization leak in author block
- `IEEE007` missing DOI for cited bibliography entries
- `BIB-CROSSCHECK` `.tex` and `.bib` cross-check (missing keys / unused entries)

### External Resources & Heuristics
- `IMG-RES` image resolution check (requires Pillow, optional)
- `LINK-VALID` URL/DOI accessibility check (requires httpx, optional)
- `PAGE-LIMIT` page count estimate (IEEE conferences typically 6-8 pages)
- `SEC-DEPTH` section nesting depth (warns on `\subsubsection` and deeper)

## Implemented Safe Fixes (6 total)

- `IEEE001` — reorder `\caption` after `\includegraphics`
- `IEEE002` — reorder `\caption` before `tabular`
- `IEEE003` — normalize `\citep` / `\citet` to `\cite`
- `IEEE009` — convert space-separated cite keys to comma-separated
- `IEEE011` — insert `\bibliographystyle{IEEEtran}` automatically
- `--prune-unused` — remove uncited entries from `.bib`

All fixes are safe (no semantic changes) and create backups by default.

## Rule Extensibility

Rules are organized per template:

- `paperfmt/core/rules/common.py`: 11 shared cross-template rules
- `paperfmt/core/rules/ieee_conf.py`: IEEE-specific rules
- `paperfmt/core/rules/acm.py`: ACM-specific rules
- `paperfmt/core/rules/neurips.py`: NeurIPS-specific rules
- `paperfmt/core/rules/acl.py`: ACL-specific rules
- `paperfmt/core/rules/__init__.py`: template-to-rule-set registry

To add a new template:
1. Create `paperfmt/core/rules/<template>.py` with a `RULES: tuple[RulePlugin, ...]`
2. Register it in `paperfmt/core/rules/__init__.py` `TEMPLATE_RULES`
3. Add template identity in `paperfmt/core/registry.py` `CANONICAL_TEMPLATES`

## Development

```bash
pip install -e ".[dev]"
python -m pytest -q         # run all tests
python -m pytest -v          # verbose output
python -m paperfmt --help    # CLI help
```
