from __future__ import annotations

import re
from pathlib import Path

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

# ---------------------------------------------------------------------------
# IEEE-specific regexes
# ---------------------------------------------------------------------------

CITE_VARIANT_RE = re.compile(r"\\cite(?:t|p)\s*\{")
CITE_VARIANT_WITH_BRACE_RE = re.compile(r"\\cite(?:t|p)(\s*\{)")
AUTHOR_BLOCK_RE = re.compile(r"\\author\s*\{(.*?)\}", re.DOTALL)
DOI_FIELD_RE = re.compile(r"^\s*doi\s*=", re.IGNORECASE | re.MULTILINE)
CITE_SPACE_SEP_RE = re.compile(r"\\cite\s*\{([^}]+)\}")
BALANCE_RE = re.compile(
    r"\\(?:balance|balancest?authors|IEEEtriggeratref|IEEEtriggercmd)\b"
)
EQ_ENV_RE = re.compile(
    r"\\begin\{equation\*?\}(.*?)\\end\{equation\*?\}", re.DOTALL
)
EQ_PUNCT_RE = re.compile(r"[.,;:!?]\s*$")


# ---------------------------------------------------------------------------
# IEEE003: citation style (citet/citep → cite)
# ---------------------------------------------------------------------------


def _check_citation_style(text: str) -> list[Diagnostic]:
    diagnostics = check_forbidden_cite_pattern(
        text,
        CITE_VARIANT_RE,
        "IEEE003",
        "Use \\cite{...} for IEEE numeric citation style.",
    )
    # IEEE003 is fixable via _fix_rule_003.
    return [
        Diagnostic(
            rule_id=d.rule_id,
            severity=d.severity,
            message=d.message,
            line=d.line,
            can_fix=True,
        )
        for d in diagnostics
    ]


def _fix_rule_003(text: str) -> tuple[str, bool]:
    updated = CITE_VARIANT_WITH_BRACE_RE.sub(r"\\cite\1", text)
    return updated, updated != text


# ---------------------------------------------------------------------------
# IEEE006: anonymization leak
# ---------------------------------------------------------------------------


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
                    message=(
                        "Possible anonymization leak in author block "
                        "for double-blind submission."
                    ),
                    line=line_of_offset(text, match.start()),
                )
            )
    return diagnostics


# ---------------------------------------------------------------------------
# IEEE007: missing DOI in bibliography entry
# ---------------------------------------------------------------------------


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


def _check_missing_doi_from_config(
    text: str, tex_file: Path, bibliography: str
) -> list[Diagnostic]:
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
                    message=(
                        f"Citation '{key}' is missing DOI in bibliography entry."
                    ),
                    line=1,
                )
            )
    return diagnostics


# ---------------------------------------------------------------------------
# IEEE008: \thanks in author block
# ---------------------------------------------------------------------------


def _check_ieee008(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if "\\thanks" not in text:
        diagnostics.append(
            Diagnostic(
                rule_id="IEEE008",
                severity="warning",
                message=(
                    "No \\thanks found; consider adding for author "
                    "affiliations/funding."
                ),
                line=1,
            )
        )
    return diagnostics


# ---------------------------------------------------------------------------
# IEEE009: comma-separated cite keys
# ---------------------------------------------------------------------------


def _check_ieee009(text: str) -> list[Diagnostic]:
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
                        message=(
                            "\\cite keys should be comma-separated, "
                            "not space-separated."
                        ),
                        line=line_of_offset(text, match.start()),
                        can_fix=True,
                    )
                )
                break
    return diagnostics


def _fix_rule_009(text: str) -> tuple[str, bool]:
    """Replace space-separated cite keys with comma-separated."""

    def _fix_cite(match: re.Match[str]) -> str:
        keys_text = match.group(1)
        keys = [k.strip() for k in keys_text.replace(",", " ").split()]
        return "\\cite{" + ", ".join(keys) + "}"

    updated = CITE_SPACE_SEP_RE.sub(_fix_cite, text)
    return updated, updated != text


# ---------------------------------------------------------------------------
# IEEE010: equation punctuation
# ---------------------------------------------------------------------------


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
                    message=(
                        "Equation should end with punctuation "
                        "(comma or period)."
                    ),
                    line=line_of_offset(text, match.start()),
                )
            )
    return diagnostics


# ---------------------------------------------------------------------------
# IEEE012: balance commands before \end{document}
# ---------------------------------------------------------------------------


def _check_ieee012(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    end_doc = text.find("\\end{document}")
    bib_match = BIBLIOGRAPHY_CMD_RE.search(text)
    if bib_match:
        between = (
            text[bib_match.end() : end_doc]
            if end_doc > bib_match.end()
            else ""
        )
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


# ---------------------------------------------------------------------------
# prune_unused_bib_entries (used by cli.py)
# ---------------------------------------------------------------------------


def prune_unused_bib_entries(
    tex_text: str, bib_text: str
) -> tuple[str, bool]:
    """Remove bibliography entries not cited in the tex file."""
    cited_keys = extract_cited_keys(tex_text)
    if not cited_keys:
        return bib_text, False

    entries = re.split(r"(?=@[a-zA-Z]+\s*\{)", bib_text)
    kept_entries: list[str] = []

    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue
        key_match = BIB_ENTRY_KEY_RE.match(entry)
        if key_match and key_match.group(1).strip() not in cited_keys:
            continue
        kept_entries.append(entry)

    result = "\n\n".join(kept_entries) + "\n"
    return result, result != bib_text


# ---------------------------------------------------------------------------
# RULES: COMMON_RULES + 12 IEEE-specific rules
# ---------------------------------------------------------------------------

RULES: tuple[RulePlugin, ...] = COMMON_RULES + (
    RulePlugin(
        "IEEE001",
        "Figure caption should be placed after includegraphics",
        "warning",
        lambda text, tex_file, ruleset: check_figure_caption_order(
            text, "IEEE001"
        ),
        fix_figure_caption_order,
    ),
    RulePlugin(
        "IEEE002",
        "Table caption should be placed before tabular",
        "warning",
        lambda text, tex_file, ruleset: check_table_caption_order(
            text, "IEEE002"
        ),
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
            text,
            "abstract",
            "IEEE004",
            "error",
            "Missing abstract environment.",
        ),
    ),
    RulePlugin(
        "IEEE005",
        "Missing IEEEkeywords environment",
        "warning",
        lambda text, tex_file, ruleset: check_required_env(
            text,
            "IEEEkeywords",
            "IEEE005",
            "warning",
            "Missing IEEEkeywords environment.",
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
        lambda text, tex_file, ruleset: _check_missing_doi_from_config(
            text, tex_file, ruleset.bibliography
        ),
    ),
    RulePlugin(
        "IEEE008",
        "Check for \\thanks presence",
        "warning",
        lambda text, tex_file, ruleset: _check_ieee008(text),
    ),
    RulePlugin(
        "IEEE009",
        "\\cite keys should be comma-separated",
        "warning",
        lambda text, tex_file, ruleset: _check_ieee009(text),
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
        lambda text: fix_bibliographystyle(text, "IEEEtran"),
    ),
    RulePlugin(
        "IEEE012",
        "Check for missing column balance command",
        "info",
        lambda text, tex_file, ruleset: _check_ieee012(text),
    ),
)
