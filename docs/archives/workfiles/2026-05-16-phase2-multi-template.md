# Phase 2: Multi-Template Support — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add ACM, NeurIPS, and ACL template support with full rule parity (~23 rules each) by extracting 11 shared rules into common.py and adding template-specific rules.

**Architecture:** Extract template-agnostic rules from `ieee_conf.py` into `rules/common.py`. Each template file (existing `ieee_conf.py`, new `acm.py`, `neurips.py`, `acl.py`) exports `RULES = COMMON_RULES + (... template rules)`. Shared helper functions in common.py reduce boilerplate for caption ordering, required environments, bibliography style checks, and citation pattern checks.

**Tech Stack:** Python 3.10+, Click, pytest, same as current codebase. No new dependencies.

---

### Task 1: Create `rules/common.py` — shared regexes and utility functions

**Files:**
- Create: `paperfmt/core/rules/common.py`

- [ ] **Step 1: Write the file with shared regexes, utilities, and helpers**

```python
from __future__ import annotations

import re
from pathlib import Path

from paperfmt.core.models import Diagnostic
from paperfmt.core.rules.base import RulePlugin

# -- Shared regexes -----------------------------------------------------------
FIGURE_RE = re.compile(r"\\begin\{figure\*?\}(.*?)\\end\{figure\*?\}", re.DOTALL)
TABLE_RE = re.compile(r"\\begin\{table\*?\}(.*?)\\end\{table\*?\}", re.DOTALL)
MANUAL_CITE_RE = re.compile(r"\[(?:\s*\d+\s*)(?:,\s*\d+\s*)*\]")
HARDCODED_REF_RE = re.compile(
    r"\b(?:Eq\.|Equation|Fig\.|Figure|Table|Tab\.)\s*(?:\(\d+\)|\d+)(?=\s|[\.,;:!\?\)]|$)",
    re.IGNORECASE,
)
GENERIC_CITE_RE = re.compile(r"\\cite[a-zA-Z]*\s*\{([^}]*)\}")
BIB_ENTRY_KEY_RE = re.compile(r"@[a-zA-Z]+\s*\{\s*([^,\s]+)\s*,")
BIBLIOGRAPHY_CMD_RE = re.compile(r"\\bibliography\s*\{([^}]+)\}")
BIB_STYLE_RE = re.compile(r"\\bibliographystyle\s*\{([^}]+)\}")
INCLUDEGRAPHICS_RE = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\s*\{([^}]+)\}")
URL_CMD_RE = re.compile(r"\\(?:url|href)\{([^}]+)\}")
SUBSECTION_RE = re.compile(r"\\subsubsection\s*\{")
LABEL_IN_ENV_RE = re.compile(
    r"\\(?:begin)\{(figure|table|equation)\*?\}(.*?)\\end\{\1\*?\}",
    re.DOTALL,
)
LABEL_RE = re.compile(r"\\label\{([^}]+)\}")


# -- Shared utilities ----------------------------------------------------------

def line_of_offset(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def extract_cited_keys(text: str) -> set[str]:
    keys: set[str] = set()
    for match in GENERIC_CITE_RE.finditer(text):
        for key in match.group(1).split(","):
            trimmed = key.strip()
            if trimmed:
                keys.add(trimmed)
    return keys


def parse_bib_keys(bib_text: str) -> set[str]:
    return {m.group(1).strip() for m in BIB_ENTRY_KEY_RE.finditer(bib_text)}


# -- Shared check functions (return list[Diagnostic]) --------------------------

def check_figure_caption_order(text: str, rule_id: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for match in FIGURE_RE.finditer(text):
        block = match.group(1)
        cap = block.find("\\caption{")
        img = block.find("\\includegraphics")
        if cap != -1 and img != -1 and cap < img:
            diagnostics.append(
                Diagnostic(
                    rule_id=rule_id,
                    severity="warning",
                    message="Figure caption should be placed after includegraphics.",
                    line=line_of_offset(text, match.start(1) + cap),
                    can_fix=True,
                )
            )
    return diagnostics


def check_table_caption_order(text: str, rule_id: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for match in TABLE_RE.finditer(text):
        block = match.group(1)
        cap = block.find("\\caption{")
        tab = block.find("\\begin{tabular")
        if cap != -1 and tab != -1 and cap > tab:
            diagnostics.append(
                Diagnostic(
                    rule_id=rule_id,
                    severity="warning",
                    message="Table caption should be placed before tabular.",
                    line=line_of_offset(text, match.start(1) + cap),
                    can_fix=True,
                )
            )
    return diagnostics


def check_manual_numeric_citations(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for match in MANUAL_CITE_RE.finditer(text):
        prefix = text[max(0, match.start() - 120) : match.start()]
        if re.search(r"\\[a-zA-Z*]+(?:\{[^{}]*\})*\s*$", prefix):
            continue
        diagnostics.append(
            Diagnostic(
                rule_id="CITE-MANUAL",
                severity="warning",
                message="Manual numeric citation detected; use \\cite{...} instead of [n].",
                line=line_of_offset(text, match.start()),
            )
        )
    return diagnostics


def check_hardcoded_cross_refs(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for match in HARDCODED_REF_RE.finditer(text):
        diagnostics.append(
            Diagnostic(
                rule_id="REF-HARDCODE",
                severity="warning",
                message="Hard-coded cross reference detected; use \\ref{...} or \\eqref{...}.",
                line=line_of_offset(text, match.start()),
            )
        )
    return diagnostics


def check_table_format_booktabs(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for match in TABLE_RE.finditer(text):
        block = match.group(1)
        if "\\hline" in block:
            diagnostics.append(
                Diagnostic(
                    rule_id="TAB-FORMAT",
                    severity="warning",
                    message="Detected \\hline in table; prefer booktabs commands (\\toprule/\\midrule/\\bottomrule).",
                    line=line_of_offset(text, match.start(1) + block.find("\\hline")),
                )
            )
    return diagnostics


def check_bib_crosscheck(text: str, tex_file: Path, bibliography: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    cited_keys = extract_cited_keys(text)
    bib_file = (tex_file.parent / bibliography).resolve()
    if not bib_file.exists():
        return diagnostics
    bib_keys = parse_bib_keys(bib_file.read_text(encoding="utf-8"))
    missing = sorted(cited_keys - bib_keys)
    unused = sorted(bib_keys - cited_keys)
    for key in missing:
        diagnostics.append(
            Diagnostic(
                rule_id="BIB-CROSSCHECK",
                severity="warning",
                message=f"Citation key '{key}' is used in tex but missing in bibliography.",
                line=1,
            )
        )
    for key in unused:
        diagnostics.append(
            Diagnostic(
                rule_id="BIB-CROSSCHECK",
                severity="warning",
                message=f"Bibliography entry '{key}' is not cited in tex.",
                line=1,
            )
        )
    return diagnostics


def check_unreferenced_labels(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    env_type_map = {"figure": "FIG-REF", "table": "TAB-REF", "equation": "EQ-REF"}
    env_names = {"figure": "Figure", "table": "Table", "equation": "Equation"}
    for env_match in LABEL_IN_ENV_RE.finditer(text):
        env_type = env_match.group(1)
        if env_type not in env_type_map:
            continue
        env_body = env_match.group(2)
        for label_match in LABEL_RE.finditer(env_body):
            label = label_match.group(1).strip()
            outside_text = text[: env_match.start()] + text[env_match.end() :]
            ref_pattern = re.compile(r"\\(?:ref|eqref)\{" + re.escape(label) + r"\}")
            if not ref_pattern.search(outside_text):
                diagnostics.append(
                    Diagnostic(
                        rule_id=env_type_map[env_type],
                        severity="warning",
                        message=f"{env_names[env_type]} label '{label}' is not referenced in text.",
                        line=line_of_offset(text, label_match.start()),
                    )
                )
    return diagnostics


def check_image_resolution(text: str, tex_file: Path) -> list[Diagnostic]:
    try:
        from PIL import Image  # type: ignore[import-untyped]
    except ImportError:
        return []
    diagnostics: list[Diagnostic] = []
    base_dir = tex_file.parent.resolve()
    for match in INCLUDEGRAPHICS_RE.finditer(text):
        img_name = match.group(1).strip()
        img_path = base_dir / img_name
        if not img_path.exists():
            continue
        try:
            with Image.open(img_path) as img:
                width_px, _ = img.size
            col_width_inches = 3.5
            dpi_est = width_px / col_width_inches
            if dpi_est < 150:
                diagnostics.append(
                    Diagnostic(
                        rule_id="IMG-RES",
                        severity="warning",
                        message=(
                            f"Image '{img_name}' resolution is low "
                            f"(~{dpi_est:.0f} DPI at column width). "
                            "Consider using 300 DPI for print."
                        ),
                        line=line_of_offset(text, match.start()),
                    )
                )
        except Exception:
            continue
    return diagnostics


def check_link_validity(text: str) -> list[Diagnostic]:
    try:
        import httpx
    except ImportError:
        return []
    diagnostics: list[Diagnostic] = []
    for match in URL_CMD_RE.finditer(text):
        url = match.group(1).strip()
        if url.startswith("doi:"):
            url = "https://doi.org/" + url[4:]
        if not url.startswith(("http://", "https://")):
            continue
        try:
            response = httpx.head(url, timeout=5, follow_redirects=True)
            if response.status_code >= 400:
                diagnostics.append(
                    Diagnostic(
                        rule_id="LINK-VALID",
                        severity="warning",
                        message=f"URL '{url[:60]}...' returned HTTP {response.status_code}.",
                        line=line_of_offset(text, match.start()),
                    )
                )
        except Exception:
            diagnostics.append(
                Diagnostic(
                    rule_id="LINK-VALID",
                    severity="warning",
                    message=f"URL '{url[:60]}...' is unreachable.",
                    line=line_of_offset(text, match.start()),
                )
            )
    return diagnostics


def check_page_limit(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    lines = text.splitlines()
    estimated_pages = len(lines) / 40.0
    if estimated_pages > 8:
        diagnostics.append(
            Diagnostic(
                rule_id="PAGE-LIMIT",
                severity="warning",
                message=(
                    f"Draft may exceed page limit (~{estimated_pages:.0f} pages estimated). "
                    "IEEE conferences typically allow 6-8 pages."
                ),
                line=1,
            )
        )
    return diagnostics


def check_section_depth(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for match in SUBSECTION_RE.finditer(text):
        diagnostics.append(
            Diagnostic(
                rule_id="SEC-DEPTH",
                severity="info",
                message="Deep section nesting (subsubsection) detected; consider flattening for conference papers.",
                line=line_of_offset(text, match.start()),
            )
        )
    return diagnostics


# -- Shared helpers (for use by template-specific rules) -----------------------

def check_required_env(text: str, env_name: str, rule_id: str, severity: str, message: str) -> list[Diagnostic]:
    if f"\\begin{{{env_name}}}" not in text:
        return [Diagnostic(rule_id=rule_id, severity=severity, message=message, line=1)]
    return []


def check_bibliographystyle(text: str, expected: str, rule_id: str, severity: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    has_bib = bool(BIBLIOGRAPHY_CMD_RE.search(text))
    style_match = BIB_STYLE_RE.search(text)
    if has_bib and not style_match:
        bib_match = BIBLIOGRAPHY_CMD_RE.search(text)
        line = line_of_offset(text, bib_match.start()) if bib_match else 1
        diagnostics.append(
            Diagnostic(
                rule_id=rule_id,
                severity=severity,
                message=f"Missing \\bibliographystyle{{{expected}}} before \\bibliography.",
                line=line,
                can_fix=True,
            )
        )
    elif has_bib and style_match and style_match.group(1).strip() != expected:
        diagnostics.append(
            Diagnostic(
                rule_id=rule_id,
                severity=severity,
                message=(
                    f"Expected \\bibliographystyle{{{expected}}} "
                    f"but found \\bibliographystyle{{{style_match.group(1).strip()}}}."
                ),
                line=line_of_offset(text, style_match.start()),
            )
        )
    return diagnostics


def check_forbidden_cite_pattern(text: str, pattern: re.Pattern[str], rule_id: str, message: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for match in pattern.finditer(text):
        diagnostics.append(
            Diagnostic(
                rule_id=rule_id,
                severity="warning",
                message=message,
                line=line_of_offset(text, match.start()),
                can_fix=True,
            )
        )
    return diagnostics


# -- Shared fix functions ------------------------------------------------------

def _fix_caption_order_for_environment(block: str, is_figure: bool) -> tuple[str, bool]:
    lines = block.splitlines()
    cap_idx = next((i for i, line in enumerate(lines) if "\\caption{" in line), None)
    anchor = "\\includegraphics" if is_figure else "\\begin{tabular"
    anchor_idx = next((i for i, line in enumerate(lines) if anchor in line), None)
    if cap_idx is None or anchor_idx is None:
        return block, False
    if is_figure and cap_idx > anchor_idx:
        return block, False
    if not is_figure and cap_idx < anchor_idx:
        return block, False
    caption_line = lines.pop(cap_idx)
    insert_at = anchor_idx + 1 if is_figure else anchor_idx
    lines.insert(insert_at, caption_line)
    return "\n".join(lines), True


def fix_figure_caption_order(text: str) -> tuple[str, bool]:
    changed_any = False

    def fix_figure(match: re.Match[str]) -> str:
        nonlocal changed_any
        block = match.group(1)
        new_block, changed = _fix_caption_order_for_environment(block, is_figure=True)
        if changed:
            changed_any = True
        return match.group(0).replace(block, new_block)

    return FIGURE_RE.sub(fix_figure, text), changed_any


def fix_table_caption_order(text: str) -> tuple[str, bool]:
    changed_any = False

    def fix_table(match: re.Match[str]) -> str:
        nonlocal changed_any
        block = match.group(1)
        new_block, changed = _fix_caption_order_for_environment(block, is_figure=False)
        if changed:
            changed_any = True
        return match.group(0).replace(block, new_block)

    return TABLE_RE.sub(fix_table, text), changed_any


def fix_bibliographystyle(text: str, expected: str) -> tuple[str, bool]:
    bib_match = BIBLIOGRAPHY_CMD_RE.search(text)
    if not bib_match:
        return text, False
    if BIB_STYLE_RE.search(text):
        return text, False
    insert_pos = bib_match.start()
    updated = text[:insert_pos] + f"\\bibliographystyle{{{expected}}}\n" + text[insert_pos:]
    return updated, True
```

- [ ] **Step 2: Verify syntax is clean**

Run: `python -c "from paperfmt.core.rules.common import COMMON_RULES"` (expected: ImportError — `COMMON_RULES` not defined yet, we'll add it in Task 2 once we port the RulePlugins)

---

### Task 2: Port 11 shared RulePlugins into `common.py` COMMON_RULES

**Files:**
- Modify: `paperfmt/core/rules/common.py` (append COMMON_RULES)

- [ ] **Step 1: Append COMMON_RULES to common.py**

Append this block to the end of `paperfmt/core/rules/common.py`:

```python
COMMON_RULES: tuple[RulePlugin, ...] = (
    RulePlugin(
        "CITE-MANUAL",
        "Manual numeric citation [n] detected",
        "warning",
        lambda text, tex_file, ruleset: check_manual_numeric_citations(text),
    ),
    RulePlugin(
        "REF-HARDCODE",
        "Hard-coded cross reference (Eq., Fig., Table)",
        "warning",
        lambda text, tex_file, ruleset: check_hardcoded_cross_refs(text),
    ),
    RulePlugin(
        "TAB-FORMAT",
        "\\hline in table; prefer booktabs commands",
        "warning",
        lambda text, tex_file, ruleset: check_table_format_booktabs(text),
    ),
    RulePlugin(
        "BIB-CROSSCHECK",
        "Cross-check citations against bibliography",
        "warning",
        lambda text, tex_file, ruleset: check_bib_crosscheck(text, tex_file, ruleset.bibliography),
    ),
    RulePlugin(
        "FIG-REF",
        "Check that figure labels are referenced in text",
        "warning",
        lambda text, tex_file, ruleset: [
            d for d in check_unreferenced_labels(text) if d.rule_id == "FIG-REF"
        ],
    ),
    RulePlugin(
        "TAB-REF",
        "Check that table labels are referenced in text",
        "warning",
        lambda text, tex_file, ruleset: [
            d for d in check_unreferenced_labels(text) if d.rule_id == "TAB-REF"
        ],
    ),
    RulePlugin(
        "EQ-REF",
        "Check that equation labels are referenced in text",
        "warning",
        lambda text, tex_file, ruleset: [
            d for d in check_unreferenced_labels(text) if d.rule_id == "EQ-REF"
        ],
    ),
    RulePlugin(
        "IMG-RES",
        "Check included image resolution for print quality",
        "warning",
        lambda text, tex_file, ruleset: check_image_resolution(text, tex_file),
    ),
    RulePlugin(
        "LINK-VALID",
        "Check URL/DOI accessibility",
        "warning",
        lambda text, tex_file, ruleset: check_link_validity(text),
    ),
    RulePlugin(
        "PAGE-LIMIT",
        "Estimate page count against conference limits",
        "warning",
        lambda text, tex_file, ruleset: check_page_limit(text),
    ),
    RulePlugin(
        "SEC-DEPTH",
        "Check section nesting depth",
        "info",
        lambda text, tex_file, ruleset: check_section_depth(text),
    ),
)
```

- [ ] **Step 2: Verify the import works**

Run: `python -c "from paperfmt.core.rules.common import COMMON_RULES; print(len(COMMON_RULES))"`
Expected: `11` and no errors.

---

### Task 3: Refactor `ieee_conf.py` to import from common

**Files:**
- Modify: `paperfmt/core/rules/ieee_conf.py` (remove shared code, import from common)

- [ ] **Step 1: Rewrite ieee_conf.py**

Replace `paperfmt/core/rules/ieee_conf.py` with:

```python
from __future__ import annotations

import re

from paperfmt.core.models import Diagnostic
from paperfmt.core.rules.base import RulePlugin
from paperfmt.core.rules.common import (
    BIBLIOGRAPHY_CMD_RE,
    BIB_STYLE_RE,
    BIB_ENTRY_KEY_RE,
    extract_cited_keys,
    check_figure_caption_order,
    check_table_caption_order,
    check_bibliographystyle,
    check_forbidden_cite_pattern,
    check_required_env,
    fix_figure_caption_order,
    fix_table_caption_order,
    fix_bibliographystyle,
    line_of_offset,
    COMMON_RULES,
)

# IEEE-specific regexes
CITE_VARIANT_RE = re.compile(r"\\cite(?:t|p)\s*\{")
CITE_VARIANT_WITH_BRACE_RE = re.compile(r"\\cite(?:t|p)(\s*\{)")
AUTHOR_BLOCK_RE = re.compile(r"\\author\s*\{(.*?)\}", re.DOTALL)
DOI_FIELD_RE = re.compile(r"^\s*doi\s*=", re.IGNORECASE | re.MULTILINE)
EQ_ENV_RE = re.compile(r"\\begin\{equation\*?\}(.*?)\\end\{equation\*?\}", re.DOTALL)
EQ_PUNCT_RE = re.compile(r"[.,;:!?]\s*$")
CITE_SPACE_SEP_RE = re.compile(r"\\cite\s*\{([^}]+)\}")
BALANCE_RE = re.compile(r"\\(?:balance|balancest?authors|IEEEtriggeratref|IEEEtriggercmd)\b")


# -- IEEE-specific checks ------------------------------------------------------

def _check_citation_style(text: str) -> list[Diagnostic]:
    return check_forbidden_cite_pattern(
        text, CITE_VARIANT_RE, "IEEE003",
        "Use \\cite{...} for IEEE numeric citation style."
    )


def _check_anonymization_leak(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for match in AUTHOR_BLOCK_RE.finditer(text):
        author_text = match.group(1).strip()
        normalized = author_text.lower()
        if not author_text:
            continue
        if "anonymous" in normalized:
            continue
        if re.search(r"[a-z]", normalized):
            diagnostics.append(
                Diagnostic(
                    rule_id="IEEE006",
                    severity="warning",
                    message="Possible anonymization leak in author block for double-blind submission.",
                    line=line_of_offset(text, match.start()),
                )
            )
    return diagnostics


def _parse_bib_doi_presence(bib_text: str) -> dict[str, bool]:
    presence: dict[str, bool] = {}
    starts = list(re.finditer(r"@[a-zA-Z]+\s*\{\s*([^,\s]+)\s*,", bib_text))
    for i, start in enumerate(starts):
        key = start.group(1).strip()
        start_idx = start.start()
        end_idx = starts[i + 1].start() if i + 1 < len(starts) else len(bib_text)
        entry_block = bib_text[start_idx:end_idx]
        presence[key] = bool(DOI_FIELD_RE.search(entry_block))
    return presence


def _check_missing_doi_from_config(text: str, tex_file: Path, bibliography: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    cited_keys = extract_cited_keys(text)
    if not cited_keys:
        return diagnostics
    bib_file = (tex_file.parent / bibliography).resolve()
    if not bib_file.exists():
        return diagnostics
    doi_presence = _parse_bib_doi_presence(bib_file.read_text(encoding="utf-8"))
    for key in sorted(cited_keys):
        if key in doi_presence and not doi_presence[key]:
            diagnostics.append(
                Diagnostic(
                    rule_id="IEEE007",
                    severity="warning",
                    message=f"Citation '{key}' is missing DOI in bibliography entry.",
                    line=1,
                )
            )
    return diagnostics


def _check_ieee_structure(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []

    # IEEE008: \thanks in author block
    if "\\thanks" not in text:
        diagnostics.append(
            Diagnostic(
                rule_id="IEEE008",
                severity="warning",
                message="No \\thanks found; consider adding for author affiliations/funding.",
                line=1,
            )
        )

    # IEEE012: balancing command before \end{document}
    end_doc = text.find("\\end{document}")
    bib_match = BIBLIOGRAPHY_CMD_RE.search(text)
    if bib_match:
        between = text[bib_match.end() : end_doc] if end_doc > bib_match.end() else ""
        if not BALANCE_RE.search(between):
            diagnostics.append(
                Diagnostic(
                    rule_id="IEEE012",
                    severity="info",
                    message=(
                        "Consider adding \\balance or \\balancest authors "
                        "before \\end{document} for two-column IEEE format."
                    ),
                    line=line_of_offset(text, bib_match.start()),
                )
            )

    return diagnostics


def _check_equation_punctuation(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for match in EQ_ENV_RE.finditer(text):
        body = match.group(1).rstrip()
        body_no_label = re.sub(r"\\label\{[^}]*\}\s*$", "", body).rstrip()
        if body_no_label and not EQ_PUNCT_RE.search(body_no_label):
            diagnostics.append(
                Diagnostic(
                    rule_id="IEEE010",
                    severity="warning",
                    message="Equation should end with punctuation (comma or period).",
                    line=line_of_offset(text, match.start()),
                )
            )
    return diagnostics


# -- IEEE-specific fixes -------------------------------------------------------

def _fix_rule_003(text: str) -> tuple[str, bool]:
    updated = CITE_VARIANT_WITH_BRACE_RE.sub(r"\\cite\1", text)
    return updated, updated != text


def _fix_rule_009(text: str) -> tuple[str, bool]:
    def _fix_cite(match: re.Match[str]) -> str:
        keys_text = match.group(1)
        keys = [k.strip() for k in keys_text.replace(",", " ").split()]
        return "\\cite{" + ", ".join(keys) + "}"
    updated = CITE_SPACE_SEP_RE.sub(_fix_cite, text)
    return updated, updated != text


def _fix_rule_011(text: str) -> tuple[str, bool]:
    return fix_bibliographystyle(text, "IEEEtran")


# -- IEEE Rules tuple ----------------------------------------------------------

RULES: tuple[RulePlugin, ...] = COMMON_RULES + (
    RulePlugin(
        "IEEE001",
        "Figure caption should be placed after includegraphics",
        "warning",
        lambda text, tex_file, ruleset: check_figure_caption_order(text, "IEEE001"),
        fix_figure_caption_order,
    ),
    RulePlugin(
        "IEEE002",
        "Table caption should be placed before tabular",
        "warning",
        lambda text, tex_file, ruleset: check_table_caption_order(text, "IEEE002"),
        fix_table_caption_order,
    ),
    RulePlugin(
        "IEEE003",
        "Use \\cite for IEEE numeric citation style",
        "warning",
        lambda text, tex_file, ruleset: _check_citation_style(text),
        _fix_rule_003,
    ),
    RulePlugin(
        "IEEE004",
        "Missing abstract environment",
        "error",
        lambda text, tex_file, ruleset: check_required_env(
            text, "abstract", "IEEE004", "error", "Missing abstract environment."
        ),
    ),
    RulePlugin(
        "IEEE005",
        "Missing IEEEkeywords environment",
        "warning",
        lambda text, tex_file, ruleset: check_required_env(
            text, "IEEEkeywords", "IEEE005", "warning", "Missing IEEEkeywords environment."
        ),
    ),
    RulePlugin(
        "IEEE006",
        "Possible anonymization leak in author block",
        "warning",
        lambda text, tex_file, ruleset: _check_anonymization_leak(text),
    ),
    RulePlugin(
        "IEEE007",
        "Cited entry missing DOI in bibliography",
        "warning",
        lambda text, tex_file, ruleset: _check_missing_doi_from_config(text, tex_file, ruleset.bibliography),
    ),
    RulePlugin(
        "IEEE008",
        "Check for \\thanks presence",
        "warning",
        lambda text, tex_file, ruleset: [
            d for d in _check_ieee_structure(text) if d.rule_id == "IEEE008"
        ],
    ),
    RulePlugin(
        "IEEE009",
        "\\cite keys should be comma-separated",
        "warning",
        lambda text, tex_file, ruleset: [
            d for d in [
                Diagnostic(
                    rule_id="IEEE009",
                    severity="warning",
                    message="\\cite keys should be comma-separated, not space-separated.",
                    line=line_of_offset(text, m.start()),
                    can_fix=True,
                )
                for m in CITE_SPACE_SEP_RE.finditer(text)
                if any(" " in k.strip() for k in m.group(1).split(",") if k.strip())
            ]
        ],
        _fix_rule_009,
    ),
    RulePlugin(
        "IEEE010",
        "Equation should end with punctuation",
        "warning",
        lambda text, tex_file, ruleset: _check_equation_punctuation(text),
    ),
    RulePlugin(
        "IEEE011",
        "Check for missing \\bibliographystyle{IEEEtran}",
        "error",
        lambda text, tex_file, ruleset: check_bibliographystyle(
            text, "IEEEtran", "IEEE011", "error"
        ),
        _fix_rule_011,
    ),
    RulePlugin(
        "IEEE012",
        "Check for missing column balance command",
        "info",
        lambda text, tex_file, ruleset: [
            d for d in _check_ieee_structure(text) if d.rule_id == "IEEE012"
        ],
    ),
)
```

Wait — the IEEE009 check lambda above is getting complex. Let me write it cleanly with a proper function.

- [ ] **Step 2: Re-read the file and verify IEEE009 check is clean**

Actually, IEEE009 is simpler kept as a function. Update the `ieee_conf.py` — replace the complex lambda for IEEE009 with a simple wrapper:

```python
def _check_ieee009(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for m in CITE_SPACE_SEP_RE.finditer(text):
        keys_text = m.group(1).strip()
        if not keys_text:
            continue
        for part in keys_text.split(","):
            if " " in part.strip():
                diagnostics.append(
                    Diagnostic(
                        rule_id="IEEE009",
                        severity="warning",
                        message="\\cite keys should be comma-separated, not space-separated.",
                        line=line_of_offset(text, m.start()),
                        can_fix=True,
                    )
                )
                break
    return diagnostics
```

And the RulePlugin becomes:
```python
    RulePlugin(
        "IEEE009",
        "\\cite keys should be comma-separated",
        "warning",
        lambda text, tex_file, ruleset: _check_ieee009(text),
        _fix_rule_009,
    ),
```

- [ ] **Step 3: Also remove the unused imports at the bottom of ieee_conf.py**

Remove the stray `import re as _re` and `from pathlib import Path as _Path` lines.

- [ ] **Step 4: Verify syntax**

Run: `python -c "from paperfmt.core.rules.ieee_conf import RULES; print(len(RULES))"`
Expected: `23` (11 common + 12 IEEE).

---

### Task 4: Update `registry.py` with new templates

**Files:**
- Modify: `paperfmt/core/registry.py`

- [ ] **Step 1: Add canonical templates**

```python
from __future__ import annotations

DEFAULT_TEMPLATE = "ieee-conf"

TEMPLATE_ALIASES: dict[str, str] = {}

CANONICAL_TEMPLATES: tuple[str, ...] = (
    DEFAULT_TEMPLATE,
    "acm-conf",
    "neurips",
    "acl-conf",
)


def normalize_template(template: str) -> str:
    return TEMPLATE_ALIASES.get(template, template)


def supported_templates() -> tuple[str, ...]:
    return CANONICAL_TEMPLATES + tuple(TEMPLATE_ALIASES.keys())


def is_supported_template(template: str) -> bool:
    return normalize_template(template) in CANONICAL_TEMPLATES
```

- [ ] **Step 2: Verify**

Run: `python -c "from paperfmt.core.registry import supported_templates; print(supported_templates())"`
Expected: `('ieee-conf', 'acm-conf', 'neurips', 'acl-conf')`

---

### Task 5: Update `rules/__init__.py` to register all templates

**Files:**
- Modify: `paperfmt/core/rules/__init__.py`

- [ ] **Step 1: Add imports for new templates**

```python
from __future__ import annotations

from paperfmt.core.registry import DEFAULT_TEMPLATE, normalize_template
from paperfmt.core.rules.base import RulePlugin
from paperfmt.core.rules.ieee_conf import RULES as IEEE_CONF_RULES
from paperfmt.core.rules.acm import RULES as ACM_RULES
from paperfmt.core.rules.neurips import RULES as NEURIPS_RULES
from paperfmt.core.rules.acl import RULES as ACL_RULES

TEMPLATE_RULES: dict[str, tuple[RulePlugin, ...]] = {
    "ieee-conf": IEEE_CONF_RULES,
    "acm-conf": ACM_RULES,
    "neurips": NEURIPS_RULES,
    "acl-conf": ACL_RULES,
}


def get_template_plugins(template: str) -> tuple[RulePlugin, ...]:
    normalized = normalize_template(template)
    return TEMPLATE_RULES.get(normalized, ())


def get_template_rule_defaults(template: str = DEFAULT_TEMPLATE) -> dict[str, str]:
    plugins = get_template_plugins(template)
    return {plugin.rule_id: plugin.default_severity for plugin in plugins}
```

(Note: `acm.RULES`, `neurips.RULES`, `acl.RULES` imports will fail until those files exist — we create them in later tasks.)

- [ ] **Step 2: Temporarily comment out new imports for now**

Since `acm.py`, `neurips.py`, `acl.py` don't exist yet, comment out those imports:

```python
from paperfmt.core.rules.ieee_conf import RULES as IEEE_CONF_RULES
# from paperfmt.core.rules.acm import RULES as ACM_RULES
# from paperfmt.core.rules.neurips import RULES as NEURIPS_RULES
# from paperfmt.core.rules.acl import RULES as ACL_RULES

TEMPLATE_RULES: dict[str, tuple[RulePlugin, ...]] = {
    "ieee-conf": IEEE_CONF_RULES,
    # "acm-conf": ACM_RULES,
    # "neurips": NEURIPS_RULES,
    # "acl-conf": ACL_RULES,
}
```

We'll uncomment in later tasks as each template file is created.

---

### Task 6: Run full test suite — verify no regression

**Files:** (none)

- [ ] **Step 1: Run all tests**

Run: `python -m pytest -v`
Expected: 34 passed.

- [ ] **Step 2: Verify ieee-conf still has 23 rules**

Run: `python -c "from paperfmt.core.rules.ieee_conf import RULES; print(len(RULES))"`
Expected: `23`

- [ ] **Step 3: Commit the refactoring**

```bash
git add paperfmt/core/rules/common.py paperfmt/core/rules/ieee_conf.py paperfmt/core/registry.py paperfmt/core/rules/__init__.py
git commit -m "refactor: extract 11 shared rules into common.py, add registry entries for new templates"
```

---

### Task 7: Create `rules/acm.py` — ACM template rules

**Files:**
- Create: `paperfmt/core/rules/acm.py`

- [ ] **Step 1: Write acm.py**

```python
from __future__ import annotations

import re
from pathlib import Path

from paperfmt.core.models import Diagnostic
from paperfmt.core.rules.base import RulePlugin
from paperfmt.core.rules.common import (
    check_figure_caption_order,
    check_table_caption_order,
    check_required_env,
    check_bibliographystyle,
    check_forbidden_cite_pattern,
    fix_figure_caption_order,
    fix_table_caption_order,
    fix_bibliographystyle,
    line_of_offset,
    COMMON_RULES,
)

# ACM-specific regexes
ACM_DOCUMENTCLASS_RE = re.compile(r"\\documentclass(?:\[[^\]]*\])?\s*\{acmart\}")
ACM_KEYWORDS_RE = re.compile(r"\\keywords\s*\{")
ACM_CCSDESC_RE = re.compile(r"\\ccsdesc\s*\{")
ACM_THANKS_RE = re.compile(r"\\thanks\s*\{")
ACM_TITLENOTE_RE = re.compile(r"\\titlenote\s*\{")
ACM_AFFILIATION_RE = re.compile(r"\\affiliation\s*\{")
ACM_EMAIL_RE = re.compile(r"\\email\s*\{")
ACM_RECEIVED_RE = re.compile(r"\\received\s*\{")
ACM_ACCEPTED_RE = re.compile(r"\\accepted\s*\{")
ACM_CITEAUTHOR_RE = re.compile(r"\\citeauthor\s*\{")
ACM_CITEYEAR_RE = re.compile(r"\\citeyear\s*\{")
ACM_CITATION_STYLE_RE = re.compile(r"\\(?:citeauthor|citeyear)\s*\{")

ACMTEXT_RE = re.compile(r"\\begin\{ACMtext\}(.*?)\\end\{ACMtext\}", re.DOTALL)


# -- ACM-specific checks -------------------------------------------------------

def _check_acm001(text: str) -> list[Diagnostic]:
    """ACM001: must have \documentclass{acmart}."""
    if not ACM_DOCUMENTCLASS_RE.search(text):
        return [
            Diagnostic(
                rule_id="ACM001",
                severity="error",
                message="Missing \\documentclass{acmart}.",
                line=1,
            )
        ]
    return []


def _check_acm002(text: str) -> list[Diagnostic]:
    return check_required_env(
        text, "keywords", "ACM002", "warning",
        "Missing \\keywords{...} command."
    )


def _check_acm003(text: str) -> list[Diagnostic]:
    return check_bibliographystyle(text, "ACM-Reference-Format", "ACM003", "error")


def _check_acm004(text: str) -> list[Diagnostic]:
    """ACM004: missing CCS concepts."""
    if not ACM_CCSDESC_RE.search(text):
        return [
            Diagnostic(
                rule_id="ACM004",
                severity="warning",
                message="Missing CCS concepts (\\ccsdesc{...}); required by ACM.",
                line=1,
            )
        ]
    return []


def _check_acm005(text: str) -> list[Diagnostic]:
    """ACM005: \thanks used (ACM uses \titlenote instead)."""
    diagnostics: list[Diagnostic] = []
    for match in ACM_THANKS_RE.finditer(text):
        diagnostics.append(
            Diagnostic(
                rule_id="ACM005",
                severity="warning",
                message="\\thanks detected; ACM uses \\titlenote{...} for title notes.",
                line=line_of_offset(text, match.start()),
            )
        )
    return diagnostics


def _check_acm006(text: str) -> list[Diagnostic]:
    """ACM006: check authors have \\affiliation."""
    diagnostics: list[Diagnostic] = []
    has_author = bool(re.search(r"\\author\s*\{", text))
    if has_author and not ACM_AFFILIATION_RE.search(text):
        diagnostics.append(
            Diagnostic(
                rule_id="ACM006",
                severity="warning",
                message="Author defined but no \\affiliation{...} found.",
                line=1,
            )
        )
    return diagnostics


def _check_acm009(text: str) -> list[Diagnostic]:
    """ACM009: missing \\received or \\accepted date fields."""
    if not ACM_RECEIVED_RE.search(text) and not ACM_ACCEPTED_RE.search(text):
        return [
            Diagnostic(
                rule_id="ACM009",
                severity="warning",
                message="Missing \\received{...} or \\accepted{...} date fields.",
                line=1,
            )
        ]
    return []


def _check_acm010(text: str) -> list[Diagnostic]:
    return check_forbidden_cite_pattern(
        text, ACM_CITATION_STYLE_RE, "ACM010",
        "Use \\cite{...} for ACM numeric citation style; avoid \\citeauthor/\\citeyear."
    )


def _check_acm011(text: str) -> list[Diagnostic]:
    """ACM011: check authors have \\email."""
    diagnostics: list[Diagnostic] = []
    has_author = bool(re.search(r"\\author\s*\{", text))
    if has_author and not ACM_EMAIL_RE.search(text):
        diagnostics.append(
            Diagnostic(
                rule_id="ACM011",
                severity="warning",
                message="Author defined but no \\email{...} found.",
                line=1,
            )
        )
    return diagnostics


def _check_acm012(text: str) -> list[Diagnostic]:
    """ACM012: check acmart format parameter matches expected venue."""
    doc_match = ACM_DOCUMENTCLASS_RE.search(text)
    if not doc_match:
        return []
    full_cmd = text[doc_match.start():doc_match.end()]
    options_match = re.search(r"\[([^\]]*)\]", full_cmd)
    if options_match:
        options = options_match.group(1)
        if "acmsmall" in options:
            return [
                Diagnostic(
                    rule_id="ACM012",
                    severity="info",
                    message="acmart 'acmsmall' format used; verify venue expects 'acmsmall' (not 'sigconf').",
                    line=line_of_offset(text, doc_match.start()),
                )
            ]
    return []


# -- ACM fixes ----------------------------------------------------------------

def _fix_acm005(text: str) -> tuple[str, bool]:
    """Replace \thanks with \titlenote."""
    updated = re.sub(r"\\thanks\s*\{", r"\\titlenote{", text)
    return updated, updated != text


def _fix_acm003(text: str) -> tuple[str, bool]:
    return fix_bibliographystyle(text, "ACM-Reference-Format")


# -- ACM RulePlugins ----------------------------------------------------------

RULES: tuple[RulePlugin, ...] = COMMON_RULES + (
    RulePlugin(
        "ACM001", "Check for \\documentclass{acmart}", "error",
        lambda text, tex_file, ruleset: _check_acm001(text),
    ),
    RulePlugin(
        "ACM002", "Check for \\keywords{...}", "warning",
        lambda text, tex_file, ruleset: _check_acm002(text),
    ),
    RulePlugin(
        "ACM003", "Check for \\bibliographystyle{ACM-Reference-Format}", "error",
        lambda text, tex_file, ruleset: _check_acm003(text),
        _fix_acm003,
    ),
    RulePlugin(
        "ACM004", "Check for CCS concepts (\\ccsdesc)", "warning",
        lambda text, tex_file, ruleset: _check_acm004(text),
    ),
    RulePlugin(
        "ACM005", "Check for \\thanks (ACM uses \\titlenote)", "warning",
        lambda text, tex_file, ruleset: _check_acm005(text),
        _fix_acm005,
    ),
    RulePlugin(
        "ACM006", "Check for \\affiliation{...} per author", "warning",
        lambda text, tex_file, ruleset: _check_acm006(text),
    ),
    RulePlugin(
        "ACM007", "Figure caption should be after \\includegraphics", "warning",
        lambda text, tex_file, ruleset: check_figure_caption_order(text, "ACM007"),
        fix_figure_caption_order,
    ),
    RulePlugin(
        "ACM008", "Table caption should be before tabular", "warning",
        lambda text, tex_file, ruleset: check_table_caption_order(text, "ACM008"),
        fix_table_caption_order,
    ),
    RulePlugin(
        "ACM009", "Check for \\received/\\accepted dates", "warning",
        lambda text, tex_file, ruleset: _check_acm009(text),
    ),
    RulePlugin(
        "ACM010", "Avoid \\citeauthor/\\citeyear; use \\cite", "warning",
        lambda text, tex_file, ruleset: _check_acm010(text),
    ),
    RulePlugin(
        "ACM011", "Check for \\email{...} per author", "warning",
        lambda text, tex_file, ruleset: _check_acm011(text),
    ),
    RulePlugin(
        "ACM012", "Check acmart format parameter", "info",
        lambda text, tex_file, ruleset: _check_acm012(text),
    ),
)
```

- [ ] **Step 2: Verify syntax and rule count**

Run: `python -c "from paperfmt.core.rules.acm import RULES; print(len(RULES))"`
Expected: `23`

- [ ] **Step 3: Uncomment ACM import in __init__.py**

Update `paperfmt/core/rules/__init__.py` — uncomment the ACM line:

```python
from paperfmt.core.rules.acm import RULES as ACM_RULES

TEMPLATE_RULES: dict[str, tuple[RulePlugin, ...]] = {
    "ieee-conf": IEEE_CONF_RULES,
    "acm-conf": ACM_RULES,
    # "neurips": NEURIPS_RULES,
    # "acl-conf": ACL_RULES,
}
```

---

### Task 8: Add ACM tests

**Files:**
- Modify: `tests/test_workflow.py` (append tests)

- [ ] **Step 1: Add ACM template tests**

Append to `tests/test_workflow.py`:

```python
# -- ACM template tests -------------------------------------------------------

_ACM_COMPLIANT = """\\documentclass[sigconf]{acmart}
\\title{Demo}
\\author{Alice}
\\affiliation{University}
\\email{alice@example.com}
\\keywords{testing, tools}
\\ccsdesc[500]{Software}
\\received{2024-01-01}
\\accepted{2024-03-01}
\\begin{document}
\\maketitle
\\begin{abstract}
Demo.
\\end{abstract}
\\bibliographystyle{ACM-Reference-Format}
\\bibliography{references}
\\end{document}
"""


def test_acm_check_compliant_no_diagnostics() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "acm-conf"])
        Path("main.tex").write_text(_ACM_COMPLIANT, encoding="utf-8")

        result = runner.invoke(main, ["check"])
        assert result.exit_code == 0
        assert "ACM001" not in result.output
        assert "ACM003" not in result.output


def test_acm_check_missing_documentclass() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "acm-conf"])
        Path("main.tex").write_text(
            """\\documentclass{article}
\\title{Demo}
\\begin{document}
\\maketitle
\\bibliographystyle{ACM-Reference-Format}
\\bibliography{references}
\\end{document}
""",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["check", "--template", "acm-conf"])
        assert "ACM001" in result.output
        assert "error" in result.output.lower() or result.exit_code != 0


def test_acm_check_missing_bibliographystyle() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "acm-conf"])
        Path("main.tex").write_text(
            """\\documentclass[sigconf]{acmart}
\\title{Demo}
\\begin{document}
\\maketitle
\\begin{abstract}
Demo.
\\end{abstract}
\\bibliography{references}
\\end{document}
""",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["check", "--template", "acm-conf"])
        assert "ACM003" in result.output


def test_acm_check_thanks_instead_of_titlenote() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "acm-conf"])
        Path("main.tex").write_text(
            """\\documentclass[sigconf]{acmart}
\\title{Demo
\\thanks{Funded by grant}}
\\author{Alice}
\\affiliation{University}
\\begin{document}
\\maketitle
\\begin{abstract}
Demo.
\\end{abstract}
\\bibliographystyle{ACM-Reference-Format}
\\bibliography{references}
\\end{document}
""",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["check", "--template", "acm-conf"])
        assert "ACM005" in result.output


def test_acm_fix_thanks_to_titlenote() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "acm-conf"])
        tex = Path("main.tex")
        tex.write_text(
            """\\documentclass[sigconf]{acmart}
\\title{Demo
\\thanks{Funded by grant}}
\\author{Alice}
\\affiliation{University}
\\begin{document}
\\maketitle
\\begin{abstract}
Demo.
\\end{abstract}
\\bibliographystyle{ACM-Reference-Format}
\\bibliography{references}
\\end{document}
""",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["fix", "--template", "acm-conf"])
        assert result.exit_code == 0
        updated = tex.read_text(encoding="utf-8")
        assert "\\thanks" not in updated
        assert "\\titlenote" in updated


def test_acm_check_common_rules_present() -> None:
    """Verify shared rules (e.g. CITE-MANUAL) fire under acm-conf template."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "acm-conf"])
        Path("main.tex").write_text(
            """\\documentclass[sigconf]{acmart}
\\title{Demo}
\\author{Alice}
\\affiliation{University}
\\begin{document}
\\maketitle
\\begin{abstract}
Demo.
\\end{abstract}
See [1] for details.
\\bibliographystyle{ACM-Reference-Format}
\\bibliography{references}
\\end{document}
""",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["check", "--template", "acm-conf"])
        assert "CITE-MANUAL" in result.output


def test_acm_check_list_rules() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "acm-conf"])
        result = runner.invoke(main, ["check", "--list-rules"])
        assert "ACM001" in result.output
        assert "CITE-MANUAL" in result.output
        assert "PAGE-LIMIT" in result.output
```

- [ ] **Step 2: Run just the ACM tests**

Run: `pytest tests/test_workflow.py -k acm -v`
Expected: 7 tests pass.

- [ ] **Step 3: Run full test suite**

Run: `python -m pytest -v`
Expected: all tests pass (34 existing + 7 new = 41).

- [ ] **Step 4: Commit**

```bash
git add paperfmt/core/rules/acm.py paperfmt/core/rules/__init__.py tests/test_workflow.py
git commit -m "feat: add acm-conf template with 12 ACM-specific rules"
```

---

### Task 9: Create `rules/neurips.py` — NeurIPS template rules

**Files:**
- Create: `paperfmt/core/rules/neurips.py`

- [ ] **Step 1: Write neurips.py**

```python
from __future__ import annotations

import re
from pathlib import Path

from paperfmt.core.models import Diagnostic
from paperfmt.core.rules.base import RulePlugin
from paperfmt.core.rules.common import (
    check_figure_caption_order,
    check_table_caption_order,
    check_required_env,
    check_bibliographystyle,
    check_forbidden_cite_pattern,
    fix_figure_caption_order,
    fix_table_caption_order,
    line_of_offset,
    BIBLIOGRAPHY_CMD_RE,
    COMMON_RULES,
)

# NeurIPS-specific regexes
NEURIPS_DOC_RE = re.compile(r"\\documentclass(?:\[[^\]]*\])?\s*\{neurips(?:_?\d+)?\}")
NEURIPS_PREPRINT_RE = re.compile(r"\\usepackage(?:\[(?:preprint|final)[^\]]*\])?\{neurips(?:_?\d+)?\}")
NEURIPS_CHECKLIST_RE = re.compile(r"(?:checklist|\bsection\{.*[Cc]hecklist)")
NEURIPS_PLAIN_BIB_RE = re.compile(r"\\bibliographystyle\s*\{(?:plain|abbrvnat|unsrtnat)\}")
NEURIPS_CITE_BARE_RE = re.compile(r"\\(?:cite|citep|citet)(?![a-zA-Z])\s*\{")
NEURIPS_CITE_BARE_ONLY_RE = re.compile(r"\\cite\s*\{")
NEURIPS_NATBIB_SKIP = re.compile(r"\\citep\s*\{|\\citet\s*\{")


def _check_neur001(text: str) -> list[Diagnostic]:
    """NEUR001: must have neurips document class."""
    if not NEURIPS_DOC_RE.search(text):
        return [
            Diagnostic(
                rule_id="NEUR001",
                severity="error",
                message="Missing \\documentclass{neurips_20XX}.",
                line=1,
            )
        ]
    return []


def _check_neur002(text: str) -> list[Diagnostic]:
    """NEUR002: check camera-ready/preprint option."""
    if not NEURIPS_PREPRINT_RE.search(text):
        return [
            Diagnostic(
                rule_id="NEUR002",
                severity="error",
                message="Missing \\usepackage[preprint]{neurips_20XX} (check camera-ready requirements).",
                line=1,
            )
        ]
    return []


def _check_neur003(text: str) -> list[Diagnostic]:
    """NEUR003: author checklist section."""
    if not NEURIPS_CHECKLIST_RE.search(text):
        return [
            Diagnostic(
                rule_id="NEUR003",
                severity="warning",
                message="Missing author checklist section; required by NeurIPS.",
                line=1,
            )
        ]
    return []


def _check_neur004(text: str) -> list[Diagnostic]:
    """NEUR004: author block should not precede abstract in anonymous style."""
    author_match = re.search(r"\\author\s*\{", text)
    abstract_match = re.search(r"\\begin\{abstract\}", text)
    if author_match and abstract_match and author_match.start() < abstract_match.start():
        return [
            Diagnostic(
                rule_id="NEUR004",
                severity="warning",
                message="\\author block should be after \\begin{abstract} for anonymous NeurIPS style.",
                line=line_of_offset(text, author_match.start()),
            )
        ]
    return []


def _check_neur005(text: str) -> list[Diagnostic]:
    """NEUR005: check bibliography style."""
    has_bib = bool(BIBLIOGRAPHY_CMD_RE.search(text))
    if has_bib and not NEURIPS_PLAIN_BIB_RE.search(text):
        bib_match = BIBLIOGRAPHY_CMD_RE.search(text)
        line = line_of_offset(text, bib_match.start()) if bib_match else 1
        return [
            Diagnostic(
                rule_id="NEUR005",
                severity="warning",
                message="Expected \\bibliographystyle{plain} or {abbrvnat} for NeurIPS.",
                line=line,
            )
        ]
    return []


def _check_neur006(text: str) -> list[Diagnostic]:
    """NEUR006: prefer \citep/\citet natbib commands over bare \cite."""
    diagnostics: list[Diagnostic] = []
    for match in NEURIPS_CITE_BARE_ONLY_RE.finditer(text):
        pos = match.start()
        # Check we're not already inside a \citep or \citet by looking back
        prefix = text[max(0, pos - 3):pos]
        if prefix.endswith("p") or prefix.endswith("t"):
            continue  # probably \citep or \citet
        diagnostics.append(
            Diagnostic(
                rule_id="NEUR006",
                severity="warning",
                message="Use \\citep{...} or \\citet{...} (natbib) for NeurIPS citations.",
                line=line_of_offset(text, pos),
                can_fix=True,
            )
        )
    return diagnostics


def _check_neur008(text: str) -> list[Diagnostic]:
    """NEUR008: check for \section{Introduction}."""
    if "\\section{Introduction}" not in text and "\\section*{Introduction}" not in text:
        return [
            Diagnostic(
                rule_id="NEUR008",
                severity="warning",
                message="Missing \\section{Introduction}.",
                line=1,
            )
        ]
    return []


def _check_neur011(text: str) -> list[Diagnostic]:
    """NEUR011: check space-separated keys in natbib citations."""
    diagnostics: list[Diagnostic] = []
    citep_t_re = re.compile(r"\\(?:citep|citet)\s*\{([^}]+)\}")
    for match in citep_t_re.finditer(text):
        keys_text = match.group(1).strip()
        if not keys_text:
            continue
        parts = [k.strip() for k in keys_text.split(",")]
        for part in parts:
            if " " in part:
                diagnostics.append(
                    Diagnostic(
                        rule_id="NEUR011",
                        severity="warning",
                        message="Citation keys should be comma-separated under natbib.",
                        line=line_of_offset(text, match.start()),
                        can_fix=True,
                    )
                )
                break
    return diagnostics


def _check_neur012(text: str) -> list[Diagnostic]:
    """NEUR012: check \balance before \end{document} for 2-column."""
    end_doc = text.find("\\end{document}")
    if "\\balance" not in text[:end_doc] if end_doc > 0 else "\\balance" not in text:
        return [
            Diagnostic(
                rule_id="NEUR012",
                severity="info",
                message="Consider adding \\balance before \\end{document} for 2-column format.",
                line=1,
            )
        ]
    return []


# -- NeurIPS fixes -------------------------------------------------------------

def _fix_neur006(text: str) -> tuple[str, bool]:
    """Replace bare \cite{X} with \citep{X} for natbib."""
    updated = re.sub(r"\\cite\s*\{", r"\\citep{", text)
    return updated, updated != text


def _fix_neur011(text: str) -> tuple[str, bool]:
    citep_t_re = re.compile(r"\\(?:citep|citet)\s*\{([^}]+)\}")

    def _fix(match: re.Match[str]) -> str:
        cmd = match.group(0)[:match.group(0).index("{")]
        keys = [k.strip() for k in match.group(1).replace(",", " ").split()]
        return cmd + "{" + ", ".join(keys) + "}"

    updated = citep_t_re.sub(_fix, text)
    return updated, updated != text


# -- NeurIPS RulePlugins -------------------------------------------------------

RULES: tuple[RulePlugin, ...] = COMMON_RULES + (
    RulePlugin(
        "NEUR001", "Check for \\documentclass{neurips_20XX}", "error",
        lambda text, tex_file, ruleset: _check_neur001(text),
    ),
    RulePlugin(
        "NEUR002", "Check for camera-ready \\usepackage[preprint]{...}", "error",
        lambda text, tex_file, ruleset: _check_neur002(text),
    ),
    RulePlugin(
        "NEUR003", "Check for author checklist section", "warning",
        lambda text, tex_file, ruleset: _check_neur003(text),
    ),
    RulePlugin(
        "NEUR004", "Author block ordering for anonymous style", "warning",
        lambda text, tex_file, ruleset: _check_neur004(text),
    ),
    RulePlugin(
        "NEUR005", "Check for \\bibliographystyle{plain} or {abbrvnat}", "warning",
        lambda text, tex_file, ruleset: _check_neur005(text),
    ),
    RulePlugin(
        "NEUR006", "Prefer \\citep{}/\\citet{} over \\cite for natbib", "warning",
        lambda text, tex_file, ruleset: _check_neur006(text),
        _fix_neur006,
    ),
    RulePlugin(
        "NEUR007", "Check for \\begin{abstract}", "error",
        lambda text, tex_file, ruleset: check_required_env(
            text, "abstract", "NEUR007", "error", "Missing abstract environment."
        ),
    ),
    RulePlugin(
        "NEUR008", "Check for \\section{Introduction}", "warning",
        lambda text, tex_file, ruleset: _check_neur008(text),
    ),
    RulePlugin(
        "NEUR009", "Figure caption should be after \\includegraphics", "warning",
        lambda text, tex_file, ruleset: check_figure_caption_order(text, "NEUR009"),
        fix_figure_caption_order,
    ),
    RulePlugin(
        "NEUR010", "Table caption should be before tabular", "warning",
        lambda text, tex_file, ruleset: check_table_caption_order(text, "NEUR010"),
        fix_table_caption_order,
    ),
    RulePlugin(
        "NEUR011", "Comma-separated citation keys under natbib", "warning",
        lambda text, tex_file, ruleset: _check_neur011(text),
        _fix_neur011,
    ),
    RulePlugin(
        "NEUR012", "Check for \\balance for 2-column", "info",
        lambda text, tex_file, ruleset: _check_neur012(text),
    ),
)
```

- [ ] **Step 2: Verify syntax and rule count**

Run: `python -c "from paperfmt.core.rules.neurips import RULES; print(len(RULES))"`
Expected: `23`

- [ ] **Step 3: Uncomment NeurIPS import in __init__.py**

---

### Task 10: Add NeurIPS tests

**Files:**
- Modify: `tests/test_workflow.py`

- [ ] **Step 1: Add NeurIPS tests**

```python
# -- NeurIPS template tests ----------------------------------------------------

_NEURIPS_COMPLIANT = """\\documentclass{neurips_2024}
\\usepackage[preprint]{neurips_2024}
\\title{Demo}
\\author{Anonymous}
\\begin{document}
\\maketitle
\\begin{abstract}
Demo.
\\end{abstract}
\\section{Introduction}
Intro text.
\\section{Author checklist}
Checklist items.
\\bibliographystyle{plain}
\\bibliography{references}
\\balance
\\end{document}
"""


def test_neurips_check_compliant_no_errors() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "neurips"])
        Path("main.tex").write_text(_NEURIPS_COMPLIANT, encoding="utf-8")

        result = runner.invoke(main, ["check", "--template", "neurips"])
        # NEUR001 and NEUR002 should not fire
        assert "NEUR001" not in result.output
        assert "NEUR002" not in result.output


def test_neurips_check_missing_documentclass() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "neurips"])
        Path("main.tex").write_text(
            """\\documentclass{article}
\\begin{document}
\\maketitle
\\begin{abstract}
Demo.
\\end{abstract}
\\end{document}
""",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["check", "--template", "neurips"])
        assert "NEUR001" in result.output


def test_neurips_check_missing_abstract() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "neurips"])
        Path("main.tex").write_text(
            """\\documentclass{neurips_2024}
\\usepackage[preprint]{neurips_2024}
\\title{Demo}
\\begin{document}
\\maketitle
\\section{Introduction}
Text.
\\end{document}
""",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["check", "--template", "neurips"])
        assert "NEUR007" in result.output


def test_neurips_check_bare_cite() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "neurips"])
        Path("main.tex").write_text(
            """\\documentclass{neurips_2024}
\\usepackage[preprint]{neurips_2024}
\\title{Demo}
\\begin{document}
\\maketitle
\\begin{abstract}
Demo.
\\end{abstract}
\\section{Introduction}
See \\cite{some_ref}.
\\bibliographystyle{plain}
\\bibliography{references}
\\end{document}
""",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["check", "--template", "neurips"])
        assert "NEUR006" in result.output


def test_neurips_fix_bare_cite_to_citep() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "neurips"])
        tex = Path("main.tex")
        tex.write_text(
            """\\documentclass{neurips_2024}
\\usepackage[preprint]{neurips_2024}
\\title{Demo}
\\begin{document}
\\maketitle
\\begin{abstract}
Demo.
\\end{abstract}
\\section{Introduction}
See \\cite{some_ref}.
\\bibliographystyle{plain}
\\bibliography{references}
\\end{document}
""",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["fix", "--template", "neurips"])
        assert result.exit_code == 0
        updated = tex.read_text(encoding="utf-8")
        assert "\\citep{some_ref}" in updated


def test_neurips_common_rules_present() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "neurips"])
        Path("main.tex").write_text(
            """\\documentclass{neurips_2024}
\\usepackage[preprint]{neurips_2024}
\\title{Demo}
\\begin{document}
\\maketitle
\\begin{abstract}
Demo.
\\end{abstract}
\\section{Introduction}
See [1] for details.
\\end{document}
""",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["check", "--template", "neurips"])
        assert "CITE-MANUAL" in result.output
```

- [ ] **Step 2: Run NeurIPS tests**

Run: `pytest tests/test_workflow.py -k neurips -v`
Expected: 6 tests pass.

- [ ] **Step 3: Run full test suite and commit**

Run: `python -m pytest -v` then commit.

---

### Task 11: Create `rules/acl.py` — ACL template rules

**Files:**
- Create: `paperfmt/core/rules/acl.py`

- [ ] **Step 1: Write acl.py**

```python
from __future__ import annotations

import re
from pathlib import Path

from paperfmt.core.models import Diagnostic
from paperfmt.core.rules.base import RulePlugin
from paperfmt.core.rules.common import (
    check_figure_caption_order,
    check_table_caption_order,
    check_required_env,
    check_bibliographystyle,
    check_forbidden_cite_pattern,
    fix_figure_caption_order,
    fix_table_caption_order,
    fix_bibliographystyle,
    line_of_offset,
    BIBLIOGRAPHY_CMD_RE,
    URL_CMD_RE,
    COMMON_RULES,
)

# ACL-specific regexes
ACL_STY_RE = re.compile(r"\\usepackage\s*\{acl\}")
ACL_DOC_ACL_RE = re.compile(r"\\documentclass(?:\[[^\]]*\])?\s*\{\[?acl\]?\}")
ACL_AUTHOR_RE = re.compile(r"\\author\s*\{")
ACL_AFFILIATION_RE = re.compile(r"\\affiliation\s*\{")
ACL_CITE_ONLY_RE = re.compile(r"\\cite\s*\{")
ACL_CITEP_CITET_RE = re.compile(r"\\(?:citep|citet)\s*\{")
ACL_FINALCOPY_RE = re.compile(r"\\aclfinalcopy")
ACL_THANKS_RE = re.compile(r"\\thanks\s*\{")
ACL_FOOTNOTE_RE = re.compile(r"\\footnote\s*\{")
ACL_URL_RE = re.compile(r"\\(?:url|href)\s*\{")
ACL_PAPERSIZE_A4_RE = re.compile(r"a4paper")
ACL_LETTERPAPER_RE = re.compile(r"letterpaper")


def _check_acl001(text: str) -> list[Diagnostic]:
    """ACL001: must have \\usepackage{acl} or appropriate documentclass."""
    if not ACL_STY_RE.search(text) and not ACL_DOC_ACL_RE.search(text):
        return [
            Diagnostic(
                rule_id="ACL001",
                severity="error",
                message="Missing \\usepackage{acl} or \\documentclass[accepted]{acl}.",
                line=1,
            )
        ]
    return []


def _check_acl002(text: str) -> list[Diagnostic]:
    """ACL002: check \\author and \\affiliation."""
    diagnostics: list[Diagnostic] = []
    if not ACL_AUTHOR_RE.search(text):
        diagnostics.append(
            Diagnostic(
                rule_id="ACL002",
                severity="warning",
                message="Missing \\author{...}.",
                line=1,
            )
        )
    if not ACL_AFFILIATION_RE.search(text):
        diagnostics.append(
            Diagnostic(
                rule_id="ACL002",
                severity="warning",
                message="Missing \\affiliation{...}.",
                line=1,
            )
        )
    return diagnostics


def _check_acl003(text: str) -> list[Diagnostic]:
    return check_bibliographystyle(text, "acl_natbib", "ACL003", "error")


def _check_acl004(text: str) -> list[Diagnostic]:
    """ACL004: prefer \\citep/\\citet over bare \\cite for ACL natbib."""
    diagnostics: list[Diagnostic] = []
    for match in ACL_CITE_ONLY_RE.finditer(text):
        pos = match.start()
        prefix = text[max(0, pos - 3):pos]
        if prefix.endswith("p") or prefix.endswith("t"):
            continue
        diagnostics.append(
            Diagnostic(
                rule_id="ACL004",
                severity="warning",
                message="Use \\citep{...} or \\citet{...} (natbib) for ACL citations.",
                line=line_of_offset(text, pos),
                can_fix=True,
            )
        )
    return diagnostics


def _check_acl008(text: str) -> list[Diagnostic]:
    """ACL008: missing Limitations or Ethics sections (ARR requirement)."""
    has_limitations = bool(re.search(r"\\section\s*\*?\s*\{[^}]*[Ll]imitations", text))
    has_ethics = bool(re.search(r"\\section\s*\*?\s*\{[^}]*[Ee]thics", text))
    if not has_limitations and not has_ethics:
        return [
            Diagnostic(
                rule_id="ACL008",
                severity="warning",
                message="Missing \\section*{Limitations} or \\section*{Ethics}; required by ARR.",
                line=1,
            )
        ]
    return []


def _check_acl009(text: str) -> list[Diagnostic]:
    """ACL009: check for data/code URL."""
    if not ACL_URL_RE.search(text):
        return [
            Diagnostic(
                rule_id="ACL009",
                severity="warning",
                message="Missing \\url{...} for data/code availability.",
                line=1,
            )
        ]
    return []


def _check_acl010(text: str) -> list[Diagnostic]:
    """ACL010: \\thanks or \\footnote in anonymous submission."""
    diagnostics: list[Diagnostic] = []
    for match in ACL_THANKS_RE.finditer(text):
        diagnostics.append(
            Diagnostic(
                rule_id="ACL010",
                severity="warning",
                message="\\thanks detected; may break anonymization for ACL/ARR submission.",
                line=line_of_offset(text, match.start()),
            )
        )
    for match in ACL_FOOTNOTE_RE.finditer(text):
        diagnostics.append(
            Diagnostic(
                rule_id="ACL010",
                severity="warning",
                message="\\footnote detected; may break anonymization for ACL/ARR submission.",
                line=line_of_offset(text, match.start()),
            )
        )
    return diagnostics


def _check_acl011(text: str) -> list[Diagnostic]:
    """ACL011: check paper size — ACL uses US letter."""
    if ACL_PAPERSIZE_A4_RE.search(text):
        return [
            Diagnostic(
                rule_id="ACL011",
                severity="warning",
                message="A4 paper detected; ACL/ARR uses US letter. Remove 'a4paper' option.",
                line=1,
            )
        ]
    return []


def _check_acl012(text: str) -> list[Diagnostic]:
    """ACL012: \\aclfinalcopy missing in camera-ready."""
    if not ACL_FINALCOPY_RE.search(text):
        return [
            Diagnostic(
                rule_id="ACL012",
                severity="info",
                message="\\aclfinalcopy not found; required for ACL camera-ready version.",
                line=1,
            )
        ]
    return []


# -- ACL fixes -----------------------------------------------------------------

def _fix_acl004(text: str) -> tuple[str, bool]:
    """Replace bare \\cite{X} with \\citep{X}."""
    updated = re.sub(r"\\cite\s*\{", r"\\citep{", text)
    return updated, updated != text


def _fix_acl003(text: str) -> tuple[str, bool]:
    return fix_bibliographystyle(text, "acl_natbib")


# -- ACL RulePlugins -----------------------------------------------------------

RULES: tuple[RulePlugin, ...] = COMMON_RULES + (
    RulePlugin(
        "ACL001", "Check for \\usepackage{acl}", "error",
        lambda text, tex_file, ruleset: _check_acl001(text),
    ),
    RulePlugin(
        "ACL002", "Check for \\author and \\affiliation", "warning",
        lambda text, tex_file, ruleset: _check_acl002(text),
    ),
    RulePlugin(
        "ACL003", "Check for \\bibliographystyle{acl_natbib}", "error",
        lambda text, tex_file, ruleset: _check_acl003(text),
        _fix_acl003,
    ),
    RulePlugin(
        "ACL004", "Prefer \\citep{}/\\citet{} over \\cite for natbib", "warning",
        lambda text, tex_file, ruleset: _check_acl004(text),
        _fix_acl004,
    ),
    RulePlugin(
        "ACL005", "Check for \\begin{abstract}", "error",
        lambda text, tex_file, ruleset: check_required_env(
            text, "abstract", "ACL005", "error", "Missing abstract environment."
        ),
    ),
    RulePlugin(
        "ACL006", "Figure caption should be after \\includegraphics", "warning",
        lambda text, tex_file, ruleset: check_figure_caption_order(text, "ACL006"),
        fix_figure_caption_order,
    ),
    RulePlugin(
        "ACL007", "Table caption should be before tabular", "warning",
        lambda text, tex_file, ruleset: check_table_caption_order(text, "ACL007"),
        fix_table_caption_order,
    ),
    RulePlugin(
        "ACL008", "Check for Limitations/Ethics sections (ARR)", "warning",
        lambda text, tex_file, ruleset: _check_acl008(text),
    ),
    RulePlugin(
        "ACL009", "Check for data/code URL", "warning",
        lambda text, tex_file, ruleset: _check_acl009(text),
    ),
    RulePlugin(
        "ACL010", "Anonymization risk: \\thanks or \\footnote", "warning",
        lambda text, tex_file, ruleset: _check_acl010(text),
    ),
    RulePlugin(
        "ACL011", "Check paper size (US letter)", "warning",
        lambda text, tex_file, ruleset: _check_acl011(text),
    ),
    RulePlugin(
        "ACL012", "Check for \\aclfinalcopy", "info",
        lambda text, tex_file, ruleset: _check_acl012(text),
    ),
)
```

- [ ] **Step 2: Uncomment ACL import in __init__.py**

---

### Task 12: Add ACL tests

**Files:**
- Modify: `tests/test_workflow.py`

- [ ] **Step 1: Add ACL tests**

```python
# -- ACL template tests --------------------------------------------------------

_ACL_COMPLIANT = """\\usepackage{acl}
\\documentclass{article}
\\title{Demo}
\\author{Anonymous}
\\affiliation{University}
\\begin{document}
\\maketitle
\\begin{abstract}
Demo.
\\end{abstract}
\\section{Introduction}
Intro.
\\section*{Limitations}
Limitations.
\\url{https://github.com/example}
\\bibliographystyle{acl_natbib}
\\bibliography{references}
\\aclfinalcopy
\\end{document}
"""


def test_acl_check_compliant_no_errors() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "acl-conf"])
        Path("main.tex").write_text(_ACL_COMPLIANT, encoding="utf-8")

        result = runner.invoke(main, ["check", "--template", "acl-conf"])
        assert "ACL001" not in result.output


def test_acl_check_missing_acl_package() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "acl-conf"])
        Path("main.tex").write_text(
            """\\documentclass{article}
\\title{Demo}
\\begin{document}
\\maketitle
\\begin{abstract}
Demo.
\\end{abstract}
\\end{document}
""",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["check", "--template", "acl-conf"])
        assert "ACL001" in result.output


def test_acl_check_missing_bibliographystyle() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "acl-conf"])
        Path("main.tex").write_text(
            """\\usepackage{acl}
\\title{Demo}
\\begin{document}
\\maketitle
\\begin{abstract}
Demo.
\\end{abstract}
\\bibliography{references}
\\end{document}
""",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["check", "--template", "acl-conf"])
        assert "ACL003" in result.output


def test_acl_check_bare_cite() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "acl-conf"])
        Path("main.tex").write_text(
            """\\usepackage{acl}
\\title{Demo}
\\begin{document}
\\maketitle
\\begin{abstract}
Demo.
\\end{abstract}
\\section{Introduction}
See \\cite{some_ref}.
\\bibliographystyle{acl_natbib}
\\bibliography{references}
\\end{document}
""",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["check", "--template", "acl-conf"])
        assert "ACL004" in result.output


def test_acl_fix_bare_cite_to_citep() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "acl-conf"])
        tex = Path("main.tex")
        tex.write_text(
            """\\usepackage{acl}
\\title{Demo}
\\begin{document}
\\maketitle
\\begin{abstract}
Demo.
\\end{abstract}
See \\cite{some_ref}.
\\bibliographystyle{acl_natbib}
\\bibliography{references}
\\end{document}
""",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["fix", "--template", "acl-conf"])
        assert result.exit_code == 0
        updated = tex.read_text(encoding="utf-8")
        assert "\\citep{some_ref}" in updated


def test_acl_check_a4paper_warning() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "acl-conf"])
        Path("main.tex").write_text(
            """\\documentclass[a4paper]{article}
\\usepackage{acl}
\\title{Demo}
\\begin{document}
\\maketitle
\\begin{abstract}
Demo.
\\end{abstract}
\\end{document}
""",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["check", "--template", "acl-conf"])
        assert "ACL011" in result.output


def test_acl_check_missing_limitations() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "acl-conf"])
        Path("main.tex").write_text(
            """\\usepackage{acl}
\\title{Demo}
\\begin{document}
\\maketitle
\\begin{abstract}
Demo.
\\end{abstract}
\\section{Introduction}
Intro.
\\bibliographystyle{acl_natbib}
\\bibliography{references}
\\end{document}
""",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["check", "--template", "acl-conf"])
        assert "ACL008" in result.output


def test_acl_common_rules_present() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "acl-conf"])
        Path("main.tex").write_text(
            """\\usepackage{acl}
\\title{Demo}
\\begin{document}
\\maketitle
\\begin{abstract}
Demo.
\\end{abstract}
\\section{Introduction}
See [1] for details and Fig. 2 shows results.
\\end{document}
""",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["check", "--template", "acl-conf"])
        assert "CITE-MANUAL" in result.output
        assert "REF-HARDCODE" in result.output
```

- [ ] **Step 2: Run ACL tests**

Run: `pytest tests/test_workflow.py -k acl -v`
Expected: 8 tests pass.

- [ ] **Step 3: Run full test suite and commit**

Run: `python -m pytest -v` then commit.

---

### Task 13: CLI integration verification and final test run

**Files:** (none — verification only)

- [ ] **Step 1: Verify `--list-rules` for all templates**

```bash
python -m paperfmt check --list-rules --template ieee-conf 2>&1 | head -5
python -m paperfmt check --list-rules --template acm-conf 2>&1 | head -5
python -m paperfmt check --list-rules --template neurips 2>&1 | head -5
python -m paperfmt check --list-rules --template acl-conf 2>&1 | head -5
```

Expected: each shows template-specific rules.

- [ ] **Step 2: Verify `init` for all templates**

```bash
python -m paperfmt init --template acm-conf --out /tmp/acm-test
python -m paperfmt init --template neurips --out /tmp/neurips-test
python -m paperfmt init --template acl-conf --out /tmp/acl-test
```

Expected: each creates paperfmt.toml with correct template name.

- [ ] **Step 3: Run full test suite**

Run: `python -m pytest -v`
Expected: all tests pass (~34 existing + 7 ACM + 6 NeurIPS + 8 ACL = ~55 tests).

- [ ] **Step 4: Commit and tag**

```bash
git add paperfmt/core/rules/acl.py tests/test_workflow.py paperfmt/core/rules/__init__.py
git commit -m "feat: add acl-conf template with 12 ACL/ARR-specific rules"
```
