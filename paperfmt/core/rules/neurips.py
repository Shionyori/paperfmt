from __future__ import annotations

import re

from paperfmt.core.models import Diagnostic
from paperfmt.core.rules.base import RulePlugin
from paperfmt.core.rules.common import (
    BIBLIOGRAPHY_CMD_RE,
    COMMON_RULES,
    check_figure_caption_order,
    check_required_env,
    check_table_caption_order,
    fix_figure_caption_order,
    fix_table_caption_order,
    line_of_offset,
)

# ---------------------------------------------------------------------------
# NeurIPS-specific regexes
# ---------------------------------------------------------------------------

NEURIPS_DOC_RE = re.compile(r"\\documentclass(?:\[[^\]]*\])?\s*\{neurips(?:_?\d+)?\}")
NEURIPS_PREPRINT_RE = re.compile(r"\\usepackage(?:\[(?:preprint|final)[^\]]*\])?\{neurips(?:_?\d+)?\}")
NEURIPS_CHECKLIST_RE = re.compile(r"(?:checklist|\bsection\{.*[Cc]hecklist)")
NEURIPS_PLAIN_BIB_RE = re.compile(r"\\bibliographystyle\s*\{(?:plain|abbrvnat|unsrtnat)\}")
NEURIPS_CITE_BARE_ONLY_RE = re.compile(r"\\cite\s*\{")


# ---------------------------------------------------------------------------
# NEUR001: Missing \documentclass{neurips_XXX}
# ---------------------------------------------------------------------------


def _check_neur001(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if not NEURIPS_DOC_RE.search(text):
        diagnostics.append(
            Diagnostic(
                rule_id="NEUR001",
                severity="error",
                message="Missing \\documentclass{neurips_XXX}.",
                line=1,
            )
        )
    return diagnostics


# ---------------------------------------------------------------------------
# NEUR002: Missing \usepackage[preprint]{neurips_XXX}
# ---------------------------------------------------------------------------


def _check_neur002(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if not NEURIPS_PREPRINT_RE.search(text):
        diagnostics.append(
            Diagnostic(
                rule_id="NEUR002",
                severity="error",
                message="Missing \\usepackage[preprint]{neurips_XXX}.",
                line=1,
            )
        )
    return diagnostics


# ---------------------------------------------------------------------------
# NEUR003: Missing author checklist section
# ---------------------------------------------------------------------------


def _check_neur003(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if not NEURIPS_CHECKLIST_RE.search(text):
        diagnostics.append(
            Diagnostic(
                rule_id="NEUR003",
                severity="warning",
                message="Missing author checklist section.",
                line=1,
            )
        )
    return diagnostics


# ---------------------------------------------------------------------------
# NEUR004: Author before abstract (anonymous style)
# ---------------------------------------------------------------------------


def _check_neur004(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    author_pos = text.find("\\author")
    abstract_pos = text.find("\\begin{abstract}")
    if author_pos != -1 and abstract_pos != -1 and author_pos < abstract_pos:
        diagnostics.append(
            Diagnostic(
                rule_id="NEUR004",
                severity="warning",
                message=("\\author should be placed after \\begin{abstract} for anonymous NeurIPS style."),
                line=line_of_offset(text, author_pos),
            )
        )
    return diagnostics


# ---------------------------------------------------------------------------
# NEUR005: Wrong/missing \bibliographystyle{plain}
# ---------------------------------------------------------------------------


def _check_neur005(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    has_bib = bool(BIBLIOGRAPHY_CMD_RE.search(text))
    if not has_bib:
        return diagnostics

    if not NEURIPS_PLAIN_BIB_RE.search(text):
        bib_match = BIBLIOGRAPHY_CMD_RE.search(text)
        line = line_of_offset(text, bib_match.start()) if bib_match else 1
        diagnostics.append(
            Diagnostic(
                rule_id="NEUR005",
                severity="warning",
                message=(
                    "Missing or incorrect \\bibliographystyle; NeurIPS expects {plain}, {abbrvnat}, or {unsrtnat}."
                ),
                line=line,
            )
        )
    return diagnostics


# ---------------------------------------------------------------------------
# NEUR006: Bare \cite instead of \citep/\citet
# ---------------------------------------------------------------------------


def _check_neur006(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for match in NEURIPS_CITE_BARE_ONLY_RE.finditer(text):
        start = match.start()
        # Exclude \citep and \citet (check char before match is not 'p' or 't')
        if start > 0 and text[start - 1] in ("p", "t"):
            continue
        diagnostics.append(
            Diagnostic(
                rule_id="NEUR006",
                severity="warning",
                message=("Use \\citep{...} or \\citet{...} instead of \\cite{...} for natbib."),
                line=line_of_offset(text, start),
                can_fix=True,
            )
        )
    return diagnostics


def _fix_neur006(text: str) -> tuple[str, bool]:
    updated = re.sub(r"\\cite\s*\{", r"\\citep{", text)
    return updated, updated != text


# ---------------------------------------------------------------------------
# NEUR007: Missing \begin{abstract}  (implemented via check_required_env)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# NEUR008: Missing \section{Introduction}
# ---------------------------------------------------------------------------


def _check_neur008(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if "\\section{Introduction}" not in text and "\\section*{Introduction}" not in text:
        diagnostics.append(
            Diagnostic(
                rule_id="NEUR008",
                severity="warning",
                message="Missing \\section{Introduction}.",
                line=1,
            )
        )
    return diagnostics


# ---------------------------------------------------------------------------
# NEUR009: Figure caption before includegraphics  (common helper + fix)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# NEUR010: Table caption after tabular  (common helper + fix)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# NEUR011: Space-separated cite keys (natbib)
# ---------------------------------------------------------------------------

_CITE_NATBIB_RE = re.compile(r"\\(?:citep|citet)\s*\{([^}]+)\}")


def _check_neur011(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for match in _CITE_NATBIB_RE.finditer(text):
        keys_text = match.group(1).strip()
        if not keys_text:
            continue
        parts = [k.strip() for k in keys_text.split(",")]
        for part in parts:
            if " " in part.strip():
                diagnostics.append(
                    Diagnostic(
                        rule_id="NEUR011",
                        severity="warning",
                        message=("\\citep/\\citet keys should be comma-separated, not space-separated."),
                        line=line_of_offset(text, match.start()),
                        can_fix=True,
                    )
                )
                break
    return diagnostics


def _fix_neur011(text: str) -> tuple[str, bool]:
    """Replace space-separated cite keys in \\citep/\\citet with comma-separated."""

    def _fix_cite(match: re.Match[str]) -> str:
        keys_text = match.group(1)
        keys = [k.strip() for k in keys_text.replace(",", " ").split()]
        cmd = match.group(0)[: match.group(0).index("{")]
        return cmd + "{" + ", ".join(keys) + "}"

    updated = _CITE_NATBIB_RE.sub(_fix_cite, text)
    return updated, updated != text


# ---------------------------------------------------------------------------
# NEUR012: Missing \balance for 2-column
# ---------------------------------------------------------------------------


def _check_neur012(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    end_doc = text.find("\\end{document}")
    if end_doc != -1:
        before_end = text[:end_doc]
        if "\\balance" not in before_end:
            diagnostics.append(
                Diagnostic(
                    rule_id="NEUR012",
                    severity="info",
                    message=("Consider adding \\balance before \\end{document} for two-column NeurIPS format."),
                    line=line_of_offset(text, end_doc),
                )
            )
    return diagnostics


# ---------------------------------------------------------------------------
# RULES: COMMON_RULES + 12 NeurIPS-specific rules
# ---------------------------------------------------------------------------

RULES: tuple[RulePlugin, ...] = COMMON_RULES + (
    RulePlugin(
        "NEUR001",
        "Check for \\documentclass{neurips_XXX}",
        "error",
        lambda text, tex_file, ruleset: _check_neur001(text),
    ),
    RulePlugin(
        "NEUR002",
        "Check for \\usepackage[preprint]{neurips_XXX}",
        "error",
        lambda text, tex_file, ruleset: _check_neur002(text),
    ),
    RulePlugin(
        "NEUR003",
        "Check for author checklist section",
        "warning",
        lambda text, tex_file, ruleset: _check_neur003(text),
    ),
    RulePlugin(
        "NEUR004",
        "Check author placement for anonymous style",
        "warning",
        lambda text, tex_file, ruleset: _check_neur004(text),
    ),
    RulePlugin(
        "NEUR005",
        "Check for \\bibliographystyle{plain}",
        "warning",
        lambda text, tex_file, ruleset: _check_neur005(text),
    ),
    RulePlugin(
        "NEUR006",
        "Use \\citep or \\citet instead of bare \\cite",
        "warning",
        lambda text, tex_file, ruleset: _check_neur006(text),
        _fix_neur006,
    ),
    RulePlugin(
        "NEUR007",
        "Missing abstract environment",
        "error",
        lambda text, tex_file, ruleset: check_required_env(
            text,
            "abstract",
            "NEUR007",
            "error",
            "Missing abstract environment.",
        ),
    ),
    RulePlugin(
        "NEUR008",
        "Check for \\section{Introduction}",
        "warning",
        lambda text, tex_file, ruleset: _check_neur008(text),
    ),
    RulePlugin(
        "NEUR009",
        "Figure caption should be placed after includegraphics",
        "warning",
        lambda text, tex_file, ruleset: check_figure_caption_order(text, "NEUR009"),
        fix_figure_caption_order,
    ),
    RulePlugin(
        "NEUR010",
        "Table caption should be placed before tabular",
        "warning",
        lambda text, tex_file, ruleset: check_table_caption_order(text, "NEUR010"),
        fix_table_caption_order,
    ),
    RulePlugin(
        "NEUR011",
        "\\citep/\\citet keys should be comma-separated",
        "warning",
        lambda text, tex_file, ruleset: _check_neur011(text),
        _fix_neur011,
    ),
    RulePlugin(
        "NEUR012",
        "Check for missing \\balance command",
        "info",
        lambda text, tex_file, ruleset: _check_neur012(text),
    ),
)
