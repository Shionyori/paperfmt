[简体中文](./README.md) | English

# paperfmt

Automated pre-submission quality checks and safe fixes for academic papers. Parses multi-file `.tex` projects, produces readable reports, and applies one-click fixes.

Supported templates: `ieee-conf` · `acm-conf` · `neurips` · `acl-conf`

## Quick Start

```bash
# Initialize in your paper directory
paperfmt init --template ieee-conf

# Run checks
paperfmt check

# Apply fixes
paperfmt fix
```

## Configuration

Example `paperfmt.toml`:

```toml
main_tex = "paper.tex"
bibliography = "refs.bib"

[rules.IEEE006]
enabled = false        # disable anonymization leak check

[rules.IEEE007]
severity = "warning"   # downgrade DOI check to warning
```

Execution logs are appended to `.paperfmt/report.txt`.

## Docs

| Document | Description |
|----------|-------------|
| [Command Reference](./docs/cli.en.md) | `init` / `check` / `fix` usage |
| [Rules](./docs/rules.en.md) | Full rule listing for all templates |
