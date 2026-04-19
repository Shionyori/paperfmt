from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path


@dataclass(slots=True)
class Diagnostic:
    rule_id: str
    severity: str
    message: str
    line: int
    can_fix: bool = False


@dataclass(slots=True)
class CheckReport:
    input_file: Path
    diagnostics: list[Diagnostic]

    @property
    def error_count(self) -> int:
        return sum(1 for d in self.diagnostics if d.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for d in self.diagnostics if d.severity == "warning")


@dataclass(slots=True)
class FixReport:
    input_file: Path
    changed: bool
    applied_fixes: list[str]
    original_text: str
    fixed_text: str


FIGURE_RE = re.compile(r"\\begin\{figure\*?\}(.*?)\\end\{figure\*?\}", re.DOTALL)
TABLE_RE = re.compile(r"\\begin\{table\*?\}(.*?)\\end\{table\*?\}", re.DOTALL)
CITE_VARIANT_RE = re.compile(r"\\cite(?:t|p)\s*\{")
CITE_VARIANT_WITH_BRACE_RE = re.compile(r"\\cite(?:t|p)(\s*\{)")


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


def run_checks(tex_file: Path, template: str) -> CheckReport:
    if template != "ieee":
        raise ValueError(f"Unsupported template: {template}")

    text = tex_file.read_text(encoding="utf-8")
    diagnostics: list[Diagnostic] = []
    diagnostics.extend(_check_figure_caption_order(text))
    diagnostics.extend(_check_table_caption_order(text))
    diagnostics.extend(_check_citation_style(text))
    diagnostics.extend(_check_required_sections(text))
    diagnostics.sort(key=lambda d: (d.line, d.rule_id))
    return CheckReport(input_file=tex_file, diagnostics=diagnostics)


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


def apply_safe_fixes(tex_file: Path, template: str) -> FixReport:
    if template != "ieee":
        raise ValueError(f"Unsupported template: {template}")

    original_text = tex_file.read_text(encoding="utf-8")
    updated_text = original_text
    applied_fixes: list[str] = []

    def fix_figure(match: re.Match[str]) -> str:
        nonlocal applied_fixes
        block = match.group(1)
        new_block, changed = _fix_caption_order_for_environment(block, is_figure=True)
        if changed:
            applied_fixes.append("IEEE001")
        return match.group(0).replace(block, new_block)

    updated_text = FIGURE_RE.sub(fix_figure, updated_text)

    def fix_table(match: re.Match[str]) -> str:
        nonlocal applied_fixes
        block = match.group(1)
        new_block, changed = _fix_caption_order_for_environment(block, is_figure=False)
        if changed:
            applied_fixes.append("IEEE002")
        return match.group(0).replace(block, new_block)

    updated_text = TABLE_RE.sub(fix_table, updated_text)

    cite_changed = CITE_VARIANT_WITH_BRACE_RE.sub(r"\\cite\1", updated_text)
    if cite_changed != updated_text:
        applied_fixes.append("IEEE003")
        updated_text = cite_changed

    return FixReport(
        input_file=tex_file,
        changed=updated_text != original_text,
        applied_fixes=applied_fixes,
        original_text=original_text,
        fixed_text=updated_text,
    )