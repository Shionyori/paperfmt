# paperfmt

paperfmt is a CLI tool for paper template compliance checks and safe auto-fixes.

Current scope:
- Input: LaTeX source file (mainly `main.tex`)
- Template: IEEE (extensible)
- Positioning: checker/fixer, not editor and not compiler wrapper

## Why this project

Users can already compile LaTeX directly.
paperfmt focuses on higher-value tasks before submission:
- detect formatting/compliance issues quickly
- provide actionable diagnostics
- apply non-semantic safe fixes

## Quick Start

1. Install:

```bash
pip install -e '.[dev]'
```

2. Initialize a starter template project:

```bash
paperfmt init --template ieee --out .
```

3. Run checks anytime:

```bash
paperfmt check main.tex --template ieee
```

4. Apply safe fixes:

```bash
paperfmt fix main.tex --template ieee
```

## Commands

```bash
paperfmt init --template ieee [--out DIR] [--force]
paperfmt check INPUT.tex [--template ieee] [--format text|json] [--strict]
paperfmt fix INPUT.tex [--template ieee] [--dry-run] [--backup/--no-backup]
```

## Current built-in checks

- Figure caption order (IEEE001)
- Table caption order (IEEE002)
- Citation style normalization target (IEEE003)
- Required abstract environment (IEEE004)
- Recommended IEEE keywords environment (IEEE005)

## Safe auto-fixes currently supported

- move figure caption below `\\includegraphics`
- move table caption above `\\begin{tabular}`
- normalize `\\citep{}` / `\\citet{}` to `\\cite{}`

## Roadmap

- Interactive preview and undo for fixes
- More submission checks: anonymization leakage, DOI completeness, image resolution, link validity
- Additional templates beyond IEEE
