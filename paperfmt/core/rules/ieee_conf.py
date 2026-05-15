from __future__ import annotations

import re
from pathlib import Path

from paperfmt.core.models import Diagnostic
from paperfmt.core.rules.base import RulePlugin

FIGURE_RE = re.compile(r"\\begin\{figure\*?\}(.*?)\\end\{figure\*?\}", re.DOTALL)
TABLE_RE = re.compile(r"\\begin\{table\*?\}(.*?)\\end\{table\*?\}", re.DOTALL)
CITE_VARIANT_RE = re.compile(r"\\cite(?:t|p)\s*\{")
CITE_VARIANT_WITH_BRACE_RE = re.compile(r"\\cite(?:t|p)(\s*\{)")
AUTHOR_BLOCK_RE = re.compile(r"\\author\s*\{(.*?)\}", re.DOTALL)
GENERIC_CITE_RE = re.compile(r"\\cite[a-zA-Z]*\s*\{([^}]*)\}")
DOI_FIELD_RE = re.compile(r"^\s*doi\s*=", re.IGNORECASE | re.MULTILINE)
MANUAL_CITE_RE = re.compile(r"\[(?:\s*\d+\s*)(?:,\s*\d+\s*)*\]")
HARDCODED_REF_RE = re.compile(
    r"\b(?:Eq\.|Equation|Fig\.|Figure|Table|Tab\.)\s*(?:\(\d+\)|\d+)(?=\s|[\.,;:!\?\)]|$)",
    re.IGNORECASE,
)
BIB_ENTRY_KEY_RE = re.compile(r"@[a-zA-Z]+\s*\{\s*([^,\s]+)\s*,")


def _line_of_offset(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _check_figure_caption_order(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for match in FIGURE_RE.finditer(text):
        block = match.group(1)
        cap = block.find("\\caption{")
        img = block.find("\\includegraphics")
        if cap != -1 and img != -1 and cap < img:
            diagnostics.append(
                Diagnostic(
                    rule_id="IEEE001",
                    severity="warning",
                    message="Figure caption should be placed after includegraphics in IEEE style.",
                    line=_line_of_offset(text, match.start(1) + cap),
                    can_fix=True,
                )
            )
    return diagnostics


def _check_table_caption_order(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for match in TABLE_RE.finditer(text):
        block = match.group(1)
        cap = block.find("\\caption{")
        tab = block.find("\\begin{tabular")
        if cap != -1 and tab != -1 and cap > tab:
            diagnostics.append(
                Diagnostic(
                    rule_id="IEEE002",
                    severity="warning",
                    message="Table caption should be placed before tabular in IEEE style.",
                    line=_line_of_offset(text, match.start(1) + cap),
                    can_fix=True,
                )
            )
    return diagnostics


def _check_citation_style(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for match in CITE_VARIANT_RE.finditer(text):
        diagnostics.append(
            Diagnostic(
                rule_id="IEEE003",
                severity="warning",
                message="Use \\cite{...} for IEEE numeric citation style.",
                line=_line_of_offset(text, match.start()),
                can_fix=True,
            )
        )
    return diagnostics


def _check_manual_numeric_citations(text: str) -> list[Diagnostic]:
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
                line=_line_of_offset(text, match.start()),
            )
        )
    return diagnostics


def _check_hardcoded_cross_refs(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for match in HARDCODED_REF_RE.finditer(text):
        diagnostics.append(
            Diagnostic(
                rule_id="REF-HARDCODE",
                severity="warning",
                message="Hard-coded cross reference detected; use \\ref{...} or \\eqref{...}.",
                line=_line_of_offset(text, match.start()),
            )
        )
    return diagnostics


def _check_required_sections(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []

    if "\\begin{abstract}" not in text:
        diagnostics.append(
            Diagnostic(
                rule_id="IEEE004",
                severity="error",
                message="Missing abstract environment.",
                line=1,
            )
        )

    if "\\begin{IEEEkeywords}" not in text:
        diagnostics.append(
            Diagnostic(
                rule_id="IEEE005",
                severity="warning",
                message="Missing IEEEkeywords environment.",
                line=1,
            )
        )

    return diagnostics


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
                    line=_line_of_offset(text, match.start()),
                )
            )
    return diagnostics


def _extract_cited_keys(text: str) -> set[str]:
    keys: set[str] = set()
    for match in GENERIC_CITE_RE.finditer(text):
        for key in match.group(1).split(","):
            trimmed = key.strip()
            if trimmed:
                keys.add(trimmed)
    return keys


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
    cited_keys = _extract_cited_keys(text)
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


BIBLIOGRAPHY_CMD_RE = re.compile(r"\\bibliography\s*\{([^}]+)\}")
BIB_STYLE_RE = re.compile(r"\\bibliographystyle\s*\{([^}]+)\}")
PARSTART_RE = re.compile(r"\\IEEEPARstart")
BALANCE_RE = re.compile(r"\\(?:balance|balancest?authors|IEEEtriggeratref|IEEEtriggercmd)\b")


def _check_ieee_structure(text: str) -> list[Diagnostic]:
    """Run IEEE008, IEEE011, IEEE012 checks, returning all diagnostics."""
    diagnostics: list[Diagnostic] = []

    # IEEE008: check for \thanks in author block
    if "\\thanks" not in text:
        diagnostics.append(
            Diagnostic(
                rule_id="IEEE008",
                severity="warning",
                message="No \\thanks found; consider adding for author affiliations/funding.",
                line=1,
            )
        )

    # IEEE011: check for \bibliographystyle{IEEEtran}
    has_bib = bool(BIBLIOGRAPHY_CMD_RE.search(text))
    has_style = bool(BIB_STYLE_RE.search(text))
    if has_bib and not has_style:
        bib_match = BIBLIOGRAPHY_CMD_RE.search(text)
        line = _line_of_offset(text, bib_match.start()) if bib_match else 1
        diagnostics.append(
            Diagnostic(
                rule_id="IEEE011",
                severity="error",
                message="Missing \\bibliographystyle{IEEEtran} before \\bibliography.",
                line=line,
                can_fix=True,
            )
        )

    # IEEE012: check for balancing commands between bibliography and end document
    end_doc = text.find("\\end{document}")
    bib_match = BIBLIOGRAPHY_CMD_RE.search(text)
    if bib_match:
        between = text[bib_match.end():end_doc] if end_doc > bib_match.end() else ""
        if not BALANCE_RE.search(between):
            diagnostics.append(
                Diagnostic(
                    rule_id="IEEE012",
                    severity="info",
                    message="Consider adding \\balance or \\balancest authors before \\end{document} for two-column IEEE format.",
                    line=_line_of_offset(text, bib_match.start()),
                )
            )

    return diagnostics


def _check_table_format_booktabs(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for match in TABLE_RE.finditer(text):
        block = match.group(1)
        if "\\hline" in block:
            diagnostics.append(
                Diagnostic(
                    rule_id="TAB-FORMAT",
                    severity="warning",
                    message="Detected \\hline in table; prefer booktabs commands (\\toprule/\\midrule/\\bottomrule).",
                    line=_line_of_offset(text, match.start(1) + block.find("\\hline")),
                )
            )
    return diagnostics


def _parse_bib_keys(bib_text: str) -> set[str]:
    return {m.group(1).strip() for m in BIB_ENTRY_KEY_RE.finditer(bib_text)}


def _check_bib_crosscheck(text: str, tex_file: Path, bibliography: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    cited_keys = _extract_cited_keys(text)

    bib_file = (tex_file.parent / bibliography).resolve()
    if not bib_file.exists():
        return diagnostics

    bib_keys = _parse_bib_keys(bib_file.read_text(encoding="utf-8"))
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
    if is_figure:
        insert_at = anchor_idx if cap_idx > anchor_idx else anchor_idx + 1
    else:
        insert_at = anchor_idx if cap_idx > anchor_idx else max(anchor_idx - 1, 0)

    lines.insert(insert_at, caption_line)
    return "\n".join(lines), True


def _fix_rule_001(text: str) -> tuple[str, bool]:
    changed_any = False

    def fix_figure(match: re.Match[str]) -> str:
        nonlocal changed_any
        block = match.group(1)
        new_block, changed = _fix_caption_order_for_environment(block, is_figure=True)
        if changed:
            changed_any = True
        return match.group(0).replace(block, new_block)

    return FIGURE_RE.sub(fix_figure, text), changed_any


def _fix_rule_002(text: str) -> tuple[str, bool]:
    changed_any = False

    def fix_table(match: re.Match[str]) -> str:
        nonlocal changed_any
        block = match.group(1)
        new_block, changed = _fix_caption_order_for_environment(block, is_figure=False)
        if changed:
            changed_any = True
        return match.group(0).replace(block, new_block)

    return TABLE_RE.sub(fix_table, text), changed_any


def _fix_rule_003(text: str) -> tuple[str, bool]:
    updated = CITE_VARIANT_WITH_BRACE_RE.sub(r"\\cite\1", text)
    return updated, updated != text


def _fix_rule_011(text: str) -> tuple[str, bool]:
    """Insert \\bibliographystyle{IEEEtran} before \\bibliography."""
    bib_match = BIBLIOGRAPHY_CMD_RE.search(text)
    if not bib_match:
        return text, False
    if BIB_STYLE_RE.search(text):
        return text, False
    insert_pos = bib_match.start()
    updated = text[:insert_pos] + "\\bibliographystyle{IEEEtran}\n" + text[insert_pos:]
    return updated, True


# IEEE009: cite keys separated by space instead of comma
CITE_SPACE_SEP_RE = re.compile(r"\\cite\s*\{([^}]+)\}")


def _check_cite_separator(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for match in CITE_SPACE_SEP_RE.finditer(text):
        keys_text = match.group(1).strip()
        if not keys_text:
            continue
        parts = [k.strip() for k in keys_text.split(",")]
        for part in parts:
            if " " in part.strip():
                diagnostics.append(
                    Diagnostic(
                        rule_id="IEEE009",
                        severity="warning",
                        message="\\cite keys should be comma-separated, not space-separated.",
                        line=_line_of_offset(text, match.start()),
                        can_fix=True,
                    )
                )
                break
    return diagnostics


# IEEE010: equation lacks trailing punctuation
EQ_ENV_RE = re.compile(r"\\begin\{equation\*?\}(.*?)\\end\{equation\*?\}", re.DOTALL)
EQ_PUNCT_RE = re.compile(r"[.,;:!?]\s*$")


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
                    line=_line_of_offset(text, match.start()),
                )
            )
    return diagnostics


def _fix_rule_009(text: str) -> tuple[str, bool]:
    """Replace space-separated cite keys with comma-separated."""

    def _fix_cite(match: re.Match[str]) -> str:
        keys_text = match.group(1)
        keys = [k.strip() for k in keys_text.replace(",", " ").split()]
        return "\\cite{" + ", ".join(keys) + "}"

    updated = CITE_SPACE_SEP_RE.sub(_fix_cite, text)
    return updated, updated != text


RULES: tuple[RulePlugin, ...] = (
    RulePlugin(
        "IEEE001",
        "Figure caption should be placed after includegraphics",
        "warning",
        lambda text, tex_file, ruleset: _check_figure_caption_order(text),
        _fix_rule_001,
    ),
    RulePlugin(
        "IEEE002",
        "Table caption should be placed before tabular",
        "warning",
        lambda text, tex_file, ruleset: _check_table_caption_order(text),
        _fix_rule_002,
    ),
    RulePlugin(
        "IEEE003",
        "Use \\cite for IEEE numeric citation style",
        "warning",
        lambda text, tex_file, ruleset: _check_citation_style(text),
        _fix_rule_003,
    ),
    RulePlugin(
        "CITE-MANUAL",
        "Manual numeric citation [n] detected",
        "warning",
        lambda text, tex_file, ruleset: _check_manual_numeric_citations(text),
    ),
    RulePlugin(
        "REF-HARDCODE",
        "Hard-coded cross reference (Eq., Fig., Table)",
        "warning",
        lambda text, tex_file, ruleset: _check_hardcoded_cross_refs(text),
    ),
    RulePlugin(
        "TAB-FORMAT",
        "\\hline in table; prefer booktabs commands",
        "warning",
        lambda text, tex_file, ruleset: _check_table_format_booktabs(text),
    ),
    RulePlugin(
        "BIB-CROSSCHECK",
        "Cross-check citations against bibliography",
        "warning",
        lambda text, tex_file, ruleset: _check_bib_crosscheck(text, tex_file, ruleset.bibliography),
    ),
    RulePlugin(
        "IEEE004",
        "Missing abstract environment",
        "error",
        lambda text, tex_file, ruleset: [d for d in _check_required_sections(text) if d.rule_id == "IEEE004"],
    ),
    RulePlugin(
        "IEEE005",
        "Missing IEEEkeywords environment",
        "warning",
        lambda text, tex_file, ruleset: [d for d in _check_required_sections(text) if d.rule_id == "IEEE005"],
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
        "Check for \\thanks and \\IEEEPARstart presence",
        "warning",
        lambda text, tex_file, ruleset: [d for d in _check_ieee_structure(text) if d.rule_id == "IEEE008"],
    ),
    RulePlugin(
        "IEEE011",
        "Check for missing \\bibliographystyle{IEEEtran}",
        "error",
        lambda text, tex_file, ruleset: [d for d in _check_ieee_structure(text) if d.rule_id == "IEEE011"],
        _fix_rule_011,
    ),
    RulePlugin(
        "IEEE012",
        "Check for missing column balance command",
        "info",
        lambda text, tex_file, ruleset: [d for d in _check_ieee_structure(text) if d.rule_id == "IEEE012"],
    ),
    RulePlugin(
        "IEEE009",
        "\\cite keys should be comma-separated",
        "warning",
        lambda text, tex_file, ruleset: _check_cite_separator(text),
        _fix_rule_009,
    ),
    RulePlugin(
        "IEEE010",
        "Equation should end with punctuation",
        "warning",
        lambda text, tex_file, ruleset: _check_equation_punctuation(text),
    ),
)
