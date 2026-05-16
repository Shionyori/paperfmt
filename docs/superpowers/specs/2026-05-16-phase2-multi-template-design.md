# Phase 2: Multi-Template Support — Design

## Goal

Extend paperfmt from 1 template (`ieee-conf`) to 4 templates covering major CS conferences:
`ieee-conf`, `acm-conf`, `neurips`, `acl-conf`. Each template has full-rule parity
(~20 rules, mix of template-specific + template-agnostic shared rules).

## File structure

```
paperfmt/core/rules/
├── __init__.py       # TEMPLATE_RULES dict, get_template_plugins()
├── base.py           # RulePlugin dataclass (unchanged)
├── common.py         # 11 template-agnostic rules + shared regexes/helpers
├── ieee_conf.py      # IEEE-specific rules (~12), imports COMMON_RULES
├── acm.py            # ACM-specific rules (~12)
├── neurips.py        # NeurIPS-specific rules (~12)
└── acl.py            # ACL-specific rules (~12)
```

Each template file exports `RULES = COMMON_RULES + (... template rules)`. `__init__.py`
imports all four template modules and registers them in `TEMPLATE_RULES`.

`registry.py`: `CANONICAL_TEMPLATES` gains `acm-conf`, `neurips`, `acl-conf`. Aliases
can be added later as requested.

## Shared rules (`common.py`)

11 rules that apply identically regardless of template:

- `BIB-CROSSCHECK` — cited keys vs `.bib` entries cross-check
- `CITE-MANUAL` — manual `[n]` citations
- `REF-HARDCODE` — hard-coded "Eq. 5" style references
- `TAB-FORMAT` — `\hline` in tables, recommend booktabs
- `FIG-REF` / `TAB-REF` / `EQ-REF` — unreferenced labels
- `IMG-RES` — low-resolution images (Pillow optional)
- `LINK-VALID` — broken URLs/DOIs (httpx optional)
- `PAGE-LIMIT` — estimated page count warning
- `SEC-DEPTH` — `\subsubsection` depth warning

## Shared helpers

To reduce boilerplate, `common.py` provides:

- `_check_required_env(text, env_name, rule_id, severity, message)` — "is `\begin{env}` present?"
- `_check_bibliographystyle(text, expected, rule_id, severity)` — bib style match
- `_check_caption_order(text, figure_rule_id, table_rule_id, severity)` — configurable caption placement
- `_check_cite_style(text, forbidden_patterns, rule_id, severity, message)` — disallowed cite variants
- `_fix_caption_order(text, ...)` — generic caption reorder fix

Template files use these to define rules declaratively where possible, falling back to
custom lambdas for template-specific needs.

## ACM template rules (`acm.py`)

| ID | Check | Severity | Fixable |
|---|---|---|---|
| ACM001 | Missing `\documentclass{acmart}` | error | — |
| ACM002 | Missing `\keywords{...}` command | warning | — |
| ACM003 | Missing `\bibliographystyle{ACM-Reference-Format}` | error | — |
| ACM004 | Missing CCS concepts (`\ccsdesc`) | warning | — |
| ACM005 | Uses `\thanks` (ACM uses `\titlenote`) | warning | — |
| ACM006 | Author missing `\affiliation{...}` | warning | — |
| ACM007 | Figure caption before `\includegraphics` | warning | yes |
| ACM008 | Table caption after `\begin{tabular}` | warning | yes |
| ACM009 | Missing `\received`/`\accepted` date fields | warning | — |
| ACM010 | Uses natbib-style cite (`\citeauthor`/`\citeyear`) | warning | — |
| ACM011 | Author missing `\email{...}` | warning | — |
| ACM012 | Wrong `acmart` format param for venue | info | — |

Combined with 11 common rules = 23 rules for `acm-conf`.

## NeurIPS template rules (`neurips.py`)

| ID | Check | Severity | Fixable |
|---|---|---|---|
| NEUR001 | Missing `\documentclass{neurips_20XX}` | error | — |
| NEUR002 | Missing `preprint` package option | error | — |
| NEUR003 | Missing author checklist section | warning | — |
| NEUR004 | Author block ordering (anonymous style) | warning | — |
| NEUR005 | Missing `\bibliographystyle{plain}` or `abbrvnat` | warning | — |
| NEUR006 | Uses `\cite{}/\cite{p}` instead of `\citep{}/\citet{}` | warning | yes |
| NEUR007 | Missing `\begin{abstract}` | error | — |
| NEUR008 | Missing `\section{Introduction}` | warning | — |
| NEUR009 | Figure caption before `\includegraphics` | warning | yes |
| NEUR010 | Table caption not above tabular | warning | yes |
| NEUR011 | Space vs comma separator in natbib cite | warning | — |
| NEUR012 | Missing `\balance` for 2-column | info | — |

Combined with 11 common rules = 23 rules for `neurips`.

## ACL template rules (`acl.py`)

| ID | Check | Severity | Fixable |
|---|---|---|---|
| ACL001 | Missing `\usepackage{acl}` | error | — |
| ACL002 | Missing `\author{...}` or `\affiliation{...}` | warning | — |
| ACL003 | Missing `\bibliographystyle{acl_natbib}` | error | — |
| ACL004 | Uses numeric `\cite` instead of natbib | warning | yes |
| ACL005 | Missing `\begin{abstract}` | error | — |
| ACL006 | Figure caption before `\includegraphics` | warning | yes |
| ACL007 | Table caption after `\begin{tabular}` | warning | yes |
| ACL008 | Missing `\section{Limitations}`/`Ethics` (ARR) | warning | — |
| ACL009 | Missing `\url{}` for data/code availability | warning | — |
| ACL010 | `\thanks`/`\footnote` in anonymous submission | warning | — |
| ACL011 | Paper size not US letter | warning | — |
| ACL012 | `\aclfinalcopy` missing in camera-ready | info | — |

Combined with 11 common rules = 23 rules for `acl-conf`.

## CLI changes

`supported_templates()` now returns 4 canonical templates. `init --template` accepts
them all. `check --template` and `fix --template` accept them all. `paperfmt.toml`
generated by `init` picks the right template name.

No new CLI flags needed. `--list-rules` already works per-template.

## Test strategy

- 11 common rules already tested via `ieee-conf`. No new common tests needed.
- Each new template gets a test class in `tests/test_workflow.py` covering:
  - Template-specific rules produce diagnostics for deviating input
  - Template-specific rules pass on compliant input
  - Fixable rules transform text correctly
  - Combined (common + template) rule count verification
- Expected total: ~34 existing + ~30 new template-specific tests = ~64 tests

## Migration / backwards compatibility

- `ieee-conf` remains the default template. Nothing breaks.
- Existing `paperfmt.toml` files continue to work. New templates use the same config schema.
- Common rules are imported by `ieee_conf.py` via `COMMON_RULES` — the 11 rules are
  no longer defined in `ieee_conf.py` but the rule IDs remain identical.

## Non-goals for Phase 2

- Auto-detection of template from `.tex` content (can be Phase 3)
- Custom user-defined rules via config (can be Phase 3)
- Parallel rule execution (not needed at current scale)
- Sub-file-level diagnostic tracking (multi-file support already works)
