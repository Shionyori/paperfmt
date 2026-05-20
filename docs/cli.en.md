# Command Reference

### `paperfmt init`

```bash
paperfmt init --template ieee-conf [--out DIR] [--force]
```

Creates `paperfmt.toml` and `.paperfmt/`. Existing `.tex` files are auto-backed up to `.paperfmt/backup/`.

### `paperfmt check`

```bash
paperfmt check [INPUT.tex] \
    [--template ieee-conf] \
    [--config paperfmt.toml] \
    [--format text|json|markdown] \
    [--list-rules] \
    [--strict]
```

- Recursively resolves `\input`/`\include` across files
- `--format markdown` outputs a Markdown table
- `--list-rules` lists all rules with enabled status
- `--strict` exits non-zero on warnings (CI-friendly)

### `paperfmt fix`

```bash
paperfmt fix [INPUT.tex] \
    [--template ieee-conf] \
    [--config paperfmt.toml] \
    [--dry-run] \
    [--backup/--no-backup] \
    [--prune-unused] \
    [--interactive]
```

- `--dry-run` shows a diff without writing files
- `--backup` creates backups before fixing (on by default)
- `--prune-unused` removes uncited entries from `.bib`
- `--interactive` / `-i` confirms each fix with `[y]es/[n]o/[s]kip rule/[a]ll/[q]uit`

All fixes are safe: cosmetic only, no semantic changes.
