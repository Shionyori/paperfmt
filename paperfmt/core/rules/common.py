from __future__ import annotations

import re
from pathlib import Path

from paperfmt.core.models import Diagnostic
from paperfmt.core.rules.base import RulePlugin

# ---------------------------------------------------------------------------
# Shared regexes
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Shared check functions
# ---------------------------------------------------------------------------


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
        # Skip command option contexts, e.g. \begin{algorithmic}[1].
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
                    message=("Detected \\hline in table; prefer booktabs commands (\\toprule/\\midrule/\\bottomrule)."),
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
    """Check that labels inside figure/table/equation are referenced in text."""
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
    """Check that included images meet minimum resolution for print."""
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
    """Check that URLs/DOIs are accessible (best-effort HEAD request)."""
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
    """Estimate if document exceeds typical conference page limit."""
    diagnostics: list[Diagnostic] = []
    lines = text.splitlines()
    estimated_pages = len(lines) / 40.0
    if estimated_pages > 8:
        diagnostics.append(
            Diagnostic(
                rule_id="PAGE-LIMIT",
                severity="warning",
                message=(f"Draft may exceed page limit (~{estimated_pages:.0f} pages estimated)."),
                line=1,
            )
        )
    return diagnostics


def check_section_depth(text: str) -> list[Diagnostic]:
    """Warn if section nesting goes too deep (past subsection)."""
    diagnostics: list[Diagnostic] = []
    for match in SUBSECTION_RE.finditer(text):
        diagnostics.append(
            Diagnostic(
                rule_id="SEC-DEPTH",
                severity="info",
                message=("Deep section nesting (subsubsection) detected; consider flattening for conference papers."),
                line=line_of_offset(text, match.start()),
            )
        )
    return diagnostics


# ---------------------------------------------------------------------------
# Shared helpers for template-specific rules
# ---------------------------------------------------------------------------


def check_required_env(text: str, env_name: str, rule_id: str, severity: str, message: str) -> list[Diagnostic]:
    """Check that a required LaTeX environment is present."""
    diagnostics: list[Diagnostic] = []
    if f"\\begin{{{env_name}}}" not in text:
        diagnostics.append(
            Diagnostic(
                rule_id=rule_id,
                severity=severity,
                message=message,
                line=1,
            )
        )
    return diagnostics


def check_bibliographystyle(text: str, expected: str, rule_id: str, severity: str) -> list[Diagnostic]:
    """Check that \\bibliographystyle matches the expected value."""
    diagnostics: list[Diagnostic] = []
    has_bib = bool(BIBLIOGRAPHY_CMD_RE.search(text))
    if not has_bib:
        return diagnostics

    style_match = BIB_STYLE_RE.search(text)
    if not style_match:
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
    elif style_match.group(1).strip() != expected:
        diagnostics.append(
            Diagnostic(
                rule_id=rule_id,
                severity="warning",
                message=(f"\\bibliographystyle should be {{{expected}}}, found {{{style_match.group(1).strip()}}}."),
                line=line_of_offset(text, style_match.start()),
                can_fix=True,
            )
        )
    return diagnostics


def check_forbidden_cite_pattern(text: str, pattern: re.Pattern[str], rule_id: str, message: str) -> list[Diagnostic]:
    """Flag occurrences of a forbidden citation pattern."""
    diagnostics: list[Diagnostic] = []
    for match in pattern.finditer(text):
        diagnostics.append(
            Diagnostic(
                rule_id=rule_id,
                severity="warning",
                message=message,
                line=line_of_offset(text, match.start()),
                can_fix=False,
            )
        )
    return diagnostics


def _fix_caption_order_for_environment(block: str, is_figure: bool) -> tuple[str, bool]:
    """Low-level caption reorder within a figure or table environment body."""
    lines = block.splitlines()
    cap_idx = next((i for i, line in enumerate(lines) if "\\caption{" in line), None)
    anchor = "\\includegraphics" if is_figure else "\\begin{tabular}"
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
    """Move \\caption after \\includegraphics within each figure environment."""
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
    """Move \\caption before \\begin{tabular} within each table environment."""
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
    """Insert or correct \\bibliographystyle before \\bibliography."""
    bib_match = BIBLIOGRAPHY_CMD_RE.search(text)
    if not bib_match:
        return text, False

    style_match = BIB_STYLE_RE.search(text)
    if style_match and style_match.group(1).strip() == expected:
        return text, False

    if style_match:
        # Replace existing non-matching style
        updated = text[: style_match.start()] + f"\\bibliographystyle{{{expected}}}" + text[style_match.end() :]
    else:
        # Insert before bibliography
        insert_pos = bib_match.start()
        updated = text[:insert_pos] + f"\\bibliographystyle{{{expected}}}\n" + text[insert_pos:]

    return updated, updated != text


# ---------------------------------------------------------------------------
# COMMON_RULES — 11 template-agnostic rules
# ---------------------------------------------------------------------------

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
        lambda text, tex_file, ruleset: [d for d in check_unreferenced_labels(text) if d.rule_id == "FIG-REF"],
    ),
    RulePlugin(
        "TAB-REF",
        "Check that table labels are referenced in text",
        "warning",
        lambda text, tex_file, ruleset: [d for d in check_unreferenced_labels(text) if d.rule_id == "TAB-REF"],
    ),
    RulePlugin(
        "EQ-REF",
        "Check that equation labels are referenced in text",
        "warning",
        lambda text, tex_file, ruleset: [d for d in check_unreferenced_labels(text) if d.rule_id == "EQ-REF"],
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
