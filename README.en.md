[简体中文](./README.md) | English

<p align="center">
  <img src="docs/icon.png" alt="paperfmt" width="128">
</p>

<h1 align="center">paperfmt</h1>

<p align="center">
  Template compliance checker and safe formatter for academic papers.
  <br>
  Parses multi-file <code>.tex</code> projects, produces readable reports, and applies one-click fixes.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-1.0.0-blue" alt="version">
  <img src="https://img.shields.io/badge/python-%E2%89%A53.10-blue" alt="python">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="license">
</p>

## Quick Start

```bash
# Initialize in your paper directory
paperfmt init --template ieee-conf

# Run checks
paperfmt check

# Apply fixes
paperfmt fix
```

## Supported Templates

| Template | Identifier | Rules | Description |
|----------|------------|-------|-------------|
| IEEE Conf | `ieee-conf` | 12 | IEEE conference paper format |
| ACM Conf | `acm-conf` | 12 | ACM conference paper format |
| NeurIPS | `neurips` | 12 | NeurIPS conference paper format |
| ACL Conf | `acl-conf` | 12 | ACL conference paper format |

All templates include 10 common rules (citation checks, label validation, image resolution, etc.).

> See [Rules](./docs/rules.en.md) for all details.

## Commands

| Command | Description |
|---------|-------------|
| `paperfmt init` | Initialize project, create `paperfmt.toml` and `.paperfmt/` |
| `paperfmt check` | Check `.tex` files, supports `--strict` CI mode, `--format json` |
| `paperfmt fix` | Safe fixes, supports `--dry-run` preview, `--interactive` mode |

> See [Command Reference](./docs/cli.en.md) for full usage.

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
