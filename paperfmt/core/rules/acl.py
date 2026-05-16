from __future__ import annotations

import re

from paperfmt.core.models import Diagnostic
from paperfmt.core.rules.base import RulePlugin
from paperfmt.core.rules.common import (
    COMMON_RULES,
    check_bibliographystyle,
    check_figure_caption_order,
    check_required_env,
    check_table_caption_order,
    fix_bibliographystyle,
    fix_figure_caption_order,
    fix_table_caption_order,
    line_of_offset,
)

# ---------------------------------------------------------------------------
# ACL-specific regexes
# ---------------------------------------------------------------------------

ACL_STY_RE = re.compile(r"\\usepackage\s*\{acl\}")
ACL_AUTHOR_RE = re.compile(r"\\author\s*\{")
ACL_AFFILIATION_RE = re.compile(r"\\affiliation\s*\{")
ACL_CITE_ONLY_RE = re.compile(r"\\cite\s*\{")
ACL_FINALCOPY_RE = re.compile(r"\\aclfinalcopy")
ACL_THANKS_RE = re.compile(r"\\thanks\s*\{")
ACL_FOOTNOTE_RE = re.compile(r"\\footnote\s*\{")
ACL_URL_RE = re.compile(r"\\(?:url|href)\s*\{")
ACL_PAPERSIZE_A4_RE = re.compile(r"a4paper")

# For ACL008: check for Limitations or Ethics sections (ARR requirement)
ACL_LIMITATIONS_ETHICS_RE = re.compile(
    r"\\section\s*\*?\s*\{[^}]*\b(?:Limitations|Ethics)\b[^}]*\}",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# ACL001: Missing \usepackage{acl}
# ---------------------------------------------------------------------------


def _check_acl001(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if not ACL_STY_RE.search(text):
        diagnostics.append(
            Diagnostic(
                rule_id="ACL001",
                severity="error",
                message="Missing \\usepackage{acl}.",
                line=1,
            )
        )
    return diagnostics


# ---------------------------------------------------------------------------
# ACL002: Missing \author or \affiliation
# ---------------------------------------------------------------------------


def _check_acl002(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if not ACL_AUTHOR_RE.search(text):
        diagnostics.append(
            Diagnostic(
                rule_id="ACL002",
                severity="warning",
                message="Missing \\author{} command.",
                line=1,
            )
        )
    if not ACL_AFFILIATION_RE.search(text):
        diagnostics.append(
            Diagnostic(
                rule_id="ACL002",
                severity="warning",
                message="Missing \\affiliation{} command.",
                line=1,
            )
        )
    return diagnostics


# ---------------------------------------------------------------------------
# ACL003: Missing \bibliographystyle{acl_natbib}  (uses common helper + fix)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# ACL004: Bare \cite instead of \citep/\citet
# ---------------------------------------------------------------------------


def _check_acl004(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for match in ACL_CITE_ONLY_RE.finditer(text):
        start = match.start()
        # Exclude \citep and \citet (check char before match is not 'p' or 't')
        if start > 0 and text[start - 1] in ("p", "t"):
            continue
        diagnostics.append(
            Diagnostic(
                rule_id="ACL004",
                severity="warning",
                message=("Use \\citep{...} or \\citet{...} instead of \\cite{...} for natbib."),
                line=line_of_offset(text, start),
                can_fix=True,
            )
        )
    return diagnostics


def _fix_acl004(text: str) -> tuple[str, bool]:
    updated = re.sub(r"\\cite\s*\{", r"\\citep{", text)
    return updated, updated != text


# ---------------------------------------------------------------------------
# ACL005: Missing \begin{abstract}  (implemented via check_required_env)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# ACL006: Figure caption before includegraphics  (common helper + fix)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# ACL007: Table caption after tabular  (common helper + fix)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# ACL008: Missing Limitations/Ethics section (ARR requirement)
# ---------------------------------------------------------------------------


def _check_acl008(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if not ACL_LIMITATIONS_ETHICS_RE.search(text):
        diagnostics.append(
            Diagnostic(
                rule_id="ACL008",
                severity="warning",
                message=("Missing \\section{Limitations} or \\section{Ethics} as required by ARR."),
                line=1,
            )
        )
    return diagnostics


# ---------------------------------------------------------------------------
# ACL009: Missing data/code URL
# ---------------------------------------------------------------------------


def _check_acl009(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if not ACL_URL_RE.search(text):
        diagnostics.append(
            Diagnostic(
                rule_id="ACL009",
                severity="warning",
                message=("Missing \\url{} or \\href{} for data/code; consider adding a link to your repository."),
                line=1,
            )
        )
    return diagnostics


# ---------------------------------------------------------------------------
# ACL010: \thanks or \footnote breaks anonymization
# ---------------------------------------------------------------------------


def _check_acl010(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for match in ACL_THANKS_RE.finditer(text):
        diagnostics.append(
            Diagnostic(
                rule_id="ACL010",
                severity="warning",
                message=("\\thanks detected; this may break anonymization for double-blind review."),
                line=line_of_offset(text, match.start()),
            )
        )
    for match in ACL_FOOTNOTE_RE.finditer(text):
        diagnostics.append(
            Diagnostic(
                rule_id="ACL010",
                severity="warning",
                message=("\\footnote detected; this may break anonymization for double-blind review."),
                line=line_of_offset(text, match.start()),
            )
        )
    return diagnostics


# ---------------------------------------------------------------------------
# ACL011: A4 paper (needs US letter)
# ---------------------------------------------------------------------------


def _check_acl011(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for match in ACL_PAPERSIZE_A4_RE.finditer(text):
        diagnostics.append(
            Diagnostic(
                rule_id="ACL011",
                severity="warning",
                message=("a4paper option detected; ACL/ARR requires US letter paper size."),
                line=line_of_offset(text, match.start()),
            )
        )
    return diagnostics


# ---------------------------------------------------------------------------
# ACL012: Missing \aclfinalcopy (camera-ready)
# ---------------------------------------------------------------------------


def _check_acl012(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if not ACL_FINALCOPY_RE.search(text):
        diagnostics.append(
            Diagnostic(
                rule_id="ACL012",
                severity="info",
                message=("Missing \\aclfinalcopy; add this command for camera-ready submissions."),
                line=1,
            )
        )
    return diagnostics


# ---------------------------------------------------------------------------
# RULES: COMMON_RULES + 12 ACL-specific rules
# ---------------------------------------------------------------------------

RULES: tuple[RulePlugin, ...] = COMMON_RULES + (
    RulePlugin(
        "ACL001",
        "Check for \\usepackage{acl}",
        "error",
        lambda text, tex_file, ruleset: _check_acl001(text),
    ),
    RulePlugin(
        "ACL002",
        "Check for \\author and \\affiliation",
        "warning",
        lambda text, tex_file, ruleset: _check_acl002(text),
    ),
    RulePlugin(
        "ACL003",
        "Check for \\bibliographystyle{acl_natbib}",
        "error",
        lambda text, tex_file, ruleset: check_bibliographystyle(text, "acl_natbib", "ACL003", "error"),
        lambda text: fix_bibliographystyle(text, "acl_natbib"),
    ),
    RulePlugin(
        "ACL004",
        "Use \\citep or \\citet instead of bare \\cite",
        "warning",
        lambda text, tex_file, ruleset: _check_acl004(text),
        _fix_acl004,
    ),
    RulePlugin(
        "ACL005",
        "Missing abstract environment",
        "error",
        lambda text, tex_file, ruleset: check_required_env(
            text,
            "abstract",
            "ACL005",
            "error",
            "Missing abstract environment.",
        ),
    ),
    RulePlugin(
        "ACL006",
        "Figure caption should be placed after includegraphics",
        "warning",
        lambda text, tex_file, ruleset: check_figure_caption_order(text, "ACL006"),
        fix_figure_caption_order,
    ),
    RulePlugin(
        "ACL007",
        "Table caption should be placed before tabular",
        "warning",
        lambda text, tex_file, ruleset: check_table_caption_order(text, "ACL007"),
        fix_table_caption_order,
    ),
    RulePlugin(
        "ACL008",
        "Check for Limitations/Ethics section (ARR)",
        "warning",
        lambda text, tex_file, ruleset: _check_acl008(text),
    ),
    RulePlugin(
        "ACL009",
        "Check for data/code URL",
        "warning",
        lambda text, tex_file, ruleset: _check_acl009(text),
    ),
    RulePlugin(
        "ACL010",
        "Check for \\thanks or \\footnote (anonymization)",
        "warning",
        lambda text, tex_file, ruleset: _check_acl010(text),
    ),
    RulePlugin(
        "ACL011",
        "Check for a4paper (needs US letter)",
        "warning",
        lambda text, tex_file, ruleset: _check_acl011(text),
    ),
    RulePlugin(
        "ACL012",
        "Check for \\aclfinalcopy (camera-ready)",
        "info",
        lambda text, tex_file, ruleset: _check_acl012(text),
    ),
)
