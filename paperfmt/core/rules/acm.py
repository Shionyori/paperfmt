from __future__ import annotations

import re

from paperfmt.core.models import Diagnostic
from paperfmt.core.rules.base import RulePlugin
from paperfmt.core.rules.common import (
    check_figure_caption_order,
    check_table_caption_order,
    check_bibliographystyle,
    check_forbidden_cite_pattern,
    fix_figure_caption_order,
    fix_table_caption_order,
    fix_bibliographystyle,
    line_of_offset,
    COMMON_RULES,
)

# ---------------------------------------------------------------------------
# ACM-specific regexes
# ---------------------------------------------------------------------------

ACM_DOCUMENTCLASS_RE = re.compile(
    r"\\documentclass(?:\[[^\]]*\])?\s*\{acmart\}"
)
ACM_KEYWORDS_RE = re.compile(r"\\keywords\s*\{")
ACM_CCSDESC_RE = re.compile(r"\\ccsdesc\s*\{")
ACM_THANKS_RE = re.compile(r"\\thanks\s*\{")
ACM_TITLENOTE_RE = re.compile(r"\\titlenote\s*\{")
ACM_AFFILIATION_RE = re.compile(r"\\affiliation\s*\{")
ACM_EMAIL_RE = re.compile(r"\\email\s*\{")
ACM_RECEIVED_RE = re.compile(r"\\received\s*\{")
ACM_ACCEPTED_RE = re.compile(r"\\accepted\s*\{")
ACM_CITATION_STYLE_RE = re.compile(r"\\(?:citeauthor|citeyear)\s*\{")
AUTHOR_CMD_RE = re.compile(r"\\author\s*\{")


# ---------------------------------------------------------------------------
# ACM001: Missing \documentclass{acmart}
# ---------------------------------------------------------------------------


def _check_acm001(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if not ACM_DOCUMENTCLASS_RE.search(text):
        diagnostics.append(
            Diagnostic(
                rule_id="ACM001",
                severity="error",
                message="Missing \\documentclass{acmart}.",
                line=1,
            )
        )
    return diagnostics


# ---------------------------------------------------------------------------
# ACM002: Missing \keywords{...}
# ---------------------------------------------------------------------------


def _check_acm002(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if not ACM_KEYWORDS_RE.search(text):
        diagnostics.append(
            Diagnostic(
                rule_id="ACM002",
                severity="warning",
                message="Missing \\keywords{...}.",
                line=1,
            )
        )
    return diagnostics


# ---------------------------------------------------------------------------
# ACM004: Missing CCS concepts (\ccsdesc)
# ---------------------------------------------------------------------------


def _check_acm004(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if not ACM_CCSDESC_RE.search(text):
        diagnostics.append(
            Diagnostic(
                rule_id="ACM004",
                severity="warning",
                message="Missing CCS concepts (\\ccsdesc{...}).",
                line=1,
            )
        )
    return diagnostics


# ---------------------------------------------------------------------------
# ACM005: \thanks used (ACM uses \titlenote)
# ---------------------------------------------------------------------------


def _check_acm005(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for match in ACM_THANKS_RE.finditer(text):
        diagnostics.append(
            Diagnostic(
                rule_id="ACM005",
                severity="warning",
                message=(
                    "\\thanks used; ACM uses \\titlenote for author notes."
                ),
                line=line_of_offset(text, match.start()),
                can_fix=True,
            )
        )
    return diagnostics


def _fix_acm005(text: str) -> tuple[str, bool]:
    updated = ACM_THANKS_RE.sub(r"\\titlenote{", text)
    return updated, updated != text


# ---------------------------------------------------------------------------
# ACM006: Author missing \affiliation{...}
# ---------------------------------------------------------------------------


def _check_acm006(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if AUTHOR_CMD_RE.search(text) and not ACM_AFFILIATION_RE.search(text):
        diagnostics.append(
            Diagnostic(
                rule_id="ACM006",
                severity="warning",
                message="Author defined but missing \\affiliation{...}.",
                line=1,
            )
        )
    return diagnostics


# ---------------------------------------------------------------------------
# ACM009: Missing \received/\accepted
# ---------------------------------------------------------------------------


def _check_acm009(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    has_received = ACM_RECEIVED_RE.search(text)
    has_accepted = ACM_ACCEPTED_RE.search(text)
    if not has_received and not has_accepted:
        diagnostics.append(
            Diagnostic(
                rule_id="ACM009",
                severity="warning",
                message=(
                    "Missing both \\received{...} and \\accepted{...}."
                ),
                line=1,
            )
        )
    return diagnostics


# ---------------------------------------------------------------------------
# ACM011: Author missing \email{...}
# ---------------------------------------------------------------------------


def _check_acm011(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if AUTHOR_CMD_RE.search(text) and not ACM_EMAIL_RE.search(text):
        diagnostics.append(
            Diagnostic(
                rule_id="ACM011",
                severity="warning",
                message="Author defined but missing \\email{...}.",
                line=1,
            )
        )
    return diagnostics


# ---------------------------------------------------------------------------
# ACM012: Wrong acmart format param
# ---------------------------------------------------------------------------


def _check_acm012(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    match = ACM_DOCUMENTCLASS_RE.search(text)
    if match:
        options = re.search(r"\[([^\]]*)\]", match.group(0))
        if options and "acmsmall" in options.group(1):
            diagnostics.append(
                Diagnostic(
                    rule_id="ACM012",
                    severity="info",
                    message=(
                        "\\documentclass option 'acmsmall' detected; "
                        "verify venue format parameter."
                    ),
                    line=line_of_offset(text, match.start()),
                )
            )
    return diagnostics


# ---------------------------------------------------------------------------
# RULES: COMMON_RULES + 12 ACM-specific rules
# ---------------------------------------------------------------------------

RULES: tuple[RulePlugin, ...] = COMMON_RULES + (
    RulePlugin(
        "ACM001",
        "Check for \\documentclass{acmart}",
        "error",
        lambda text, tex_file, ruleset: _check_acm001(text),
    ),
    RulePlugin(
        "ACM002",
        "Check for \\keywords{...}",
        "warning",
        lambda text, tex_file, ruleset: _check_acm002(text),
    ),
    RulePlugin(
        "ACM003",
        "Check for missing \\bibliographystyle{ACM-Reference-Format}",
        "error",
        lambda text, tex_file, ruleset: check_bibliographystyle(
            text, "ACM-Reference-Format", "ACM003", "error"
        ),
        lambda text: fix_bibliographystyle(text, "ACM-Reference-Format"),
    ),
    RulePlugin(
        "ACM004",
        "Check for missing CCS concepts (\\ccsdesc)",
        "warning",
        lambda text, tex_file, ruleset: _check_acm004(text),
    ),
    RulePlugin(
        "ACM005",
        "Check for \\thanks (ACM uses \\titlenote)",
        "warning",
        lambda text, tex_file, ruleset: _check_acm005(text),
        _fix_acm005,
    ),
    RulePlugin(
        "ACM006",
        "Check author has \\affiliation{...}",
        "warning",
        lambda text, tex_file, ruleset: _check_acm006(text),
    ),
    RulePlugin(
        "ACM007",
        "Figure caption should be placed after includegraphics",
        "warning",
        lambda text, tex_file, ruleset: check_figure_caption_order(
            text, "ACM007"
        ),
        fix_figure_caption_order,
    ),
    RulePlugin(
        "ACM008",
        "Table caption should be placed before tabular",
        "warning",
        lambda text, tex_file, ruleset: check_table_caption_order(
            text, "ACM008"
        ),
        fix_table_caption_order,
    ),
    RulePlugin(
        "ACM009",
        "Check for missing \\received/\\accepted",
        "warning",
        lambda text, tex_file, ruleset: _check_acm009(text),
    ),
    RulePlugin(
        "ACM010",
        "Use \\cite instead of \\citeauthor/\\citeyear",
        "warning",
        lambda text, tex_file, ruleset: check_forbidden_cite_pattern(
            text,
            ACM_CITATION_STYLE_RE,
            "ACM010",
            "Use \\cite{...} instead of \\citeauthor or \\citeyear.",
        ),
    ),
    RulePlugin(
        "ACM011",
        "Check author has \\email{...}",
        "warning",
        lambda text, tex_file, ruleset: _check_acm011(text),
    ),
    RulePlugin(
        "ACM012",
        "Check for wrong acmart format parameter",
        "info",
        lambda text, tex_file, ruleset: _check_acm012(text),
    ),
)
