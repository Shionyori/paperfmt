# Rules

### ieee-conf

| Rule | Description | Severity | Fixable |
|------|-------------|----------|---------|
| `IEEE001` | Figure caption should be after `\includegraphics` | warning | ✓ |
| `IEEE002` | Table caption should be before `tabular` | warning | ✓ |
| `IEEE003` | Normalize `\citep`/`\citet` to `\cite` | warning | ✓ |
| `IEEE004` | Missing `abstract` environment | error | |
| `IEEE005` | Missing `IEEEkeywords` environment | warning | ✓ |
| `IEEE006` | Anonymization leak in author block | warning | |
| `IEEE007` | Missing DOI for cited entries | warning | |
| `IEEE008` | Missing `\thanks` for author/funding info | warning | |
| `IEEE009` | `\cite` keys should be comma-separated | warning | ✓ |
| `IEEE010` | Equation environment missing trailing punctuation | warning | ✓ |
| `IEEE011` | Missing `\bibliographystyle{IEEEtran}` | error | ✓ |
| `IEEE012` | Missing `\balance` column balancing command | info | ✓ |

### acm-conf

| Rule | Description | Severity | Fixable |
|------|-------------|----------|---------|
| `ACM001` | Missing `\documentclass{acmart}` | error | |
| `ACM002` | Missing `\keywords{...}` | warning | |
| `ACM003` | Missing `\bibliographystyle{ACM-Reference-Format}` | error | ✓ |
| `ACM004` | Missing CCS concepts (`\ccsdesc`) | warning | |
| `ACM005` | `\thanks` should be `\titlenote` in ACM | warning | ✓ |
| `ACM006` | Author missing `\affiliation{...}` | warning | |
| `ACM007` | Figure caption should be after `\includegraphics` | warning | ✓ |
| `ACM008` | Table caption should be before `tabular` | warning | ✓ |
| `ACM009` | Missing `\received`/`\accepted` | warning | |
| `ACM010` | Use `\cite` instead of `\citeauthor`/`\citeyear` | warning | |
| `ACM011` | Author missing `\email{...}` | warning | |
| `ACM012` | Verify `acmsmall` format parameter | info | |

### neurips

| Rule | Description | Severity | Fixable |
|------|-------------|----------|---------|
| `NEUR001` | Missing `\documentclass{neurips_XXX}` | error | |
| `NEUR002` | Missing `\usepackage[preprint]{neurips_XXX}` | error | |
| `NEUR003` | Missing author checklist section | warning | |
| `NEUR004` | `\author` should be after `\begin{abstract}` | warning | |
| `NEUR005` | `\bibliographystyle` should be `{plain}` etc. | warning | |
| `NEUR006` | Use `\citep`/`\citet` instead of bare `\cite` | warning | ✓ |
| `NEUR007` | Missing `abstract` environment | error | |
| `NEUR008` | Missing `\section{Introduction}` | warning | |
| `NEUR009` | Figure caption should be after `\includegraphics` | warning | ✓ |
| `NEUR010` | Table caption should be before `tabular` | warning | ✓ |
| `NEUR011` | `\citep`/`\citet` keys should be comma-separated | warning | ✓ |
| `NEUR012` | Missing `\balance` column balancing command | info | |

### acl-conf

| Rule | Description | Severity | Fixable |
|------|-------------|----------|---------|
| `ACL001` | Missing `\usepackage{acl}` | error | |
| `ACL002` | Missing `\author` or `\affiliation` | warning | |
| `ACL003` | Missing `\bibliographystyle{acl_natbib}` | error | ✓ |
| `ACL004` | Use `\citep`/`\citet` instead of bare `\cite` | warning | ✓ |
| `ACL005` | Missing `abstract` environment | error | |
| `ACL006` | Figure caption should be after `\includegraphics` | warning | ✓ |
| `ACL007` | Table caption should be before `tabular` | warning | ✓ |
| `ACL008` | Missing Limitations/Ethics section (ARR) | warning | |
| `ACL009` | Missing data/code repository link | warning | |
| `ACL010` | `\thanks`/`\footnote` may break anonymization | warning | |
| `ACL011` | `a4paper` should be US letter | warning | |
| `ACL012` | Missing `\aclfinalcopy` (camera-ready) | info | |

### Common Rules (shared by all templates)

| Rule | Description | Severity | Optional Dep |
|------|-------------|----------|-------------|
| `CITE-MANUAL` | Manual numeric citations (e.g. `[1]`), use `\cite` | warning | |
| `REF-HARDCODE` | Hardcoded cross-references (e.g. `Eq. (1)`), use `\ref` | warning | |
| `TAB-FORMAT` | `\hline` in table; prefer booktabs commands | warning | |
| `BIB-CROSSCHECK` | `.tex` ↔ `.bib` cross-check | warning | |
| `FIG-REF` | Figure label not referenced in text | warning | |
| `TAB-REF` | Table label not referenced in text | warning | |
| `EQ-REF` | Equation label not referenced in text | warning | |
| `IMG-RES` | Image resolution check (300 DPI recommended) | warning | Pillow |
| `LINK-VALID` | URL/DOI accessibility check | warning | httpx |
| `PAGE-LIMIT` | Page count estimate | warning | |
| `SEC-DEPTH` | Section nesting depth (`\subsubsection`+) | info | |
