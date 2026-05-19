# Phase 1: 夯实核心 — 深化 ieee-conf 规则与修复 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 ieee-conf 规则从 11 条扩展到 23+ 条，新增 3 条自动修复，支持多文件项目和 markdown 报告格式。

**Architecture:** 所有新规则在 `paperfmt/core/rules/ieee_conf.py` 中实现，遵循现有 `RulePlugin` 模式。多文件支持通过在 `checker.py` 中添加 `\input`/`\include` 递归解析实现。CLI 增强（markdown 格式、`--list-rules`）在 `cli.py` 中完成。

**Tech Stack:** Python 3.10+, click, pytest, Pillow (optional), httpx (optional)

---

### Task 1: CLI 增强 — `--format markdown` 与 RulePlugin.description

**Files:**
- Modify: `paperfmt/core/rules/base.py` — 添加 `description` 字段
- Modify: `paperfmt/core/rules/ieee_conf.py` — 为现有 11 条规则添加 description
- Modify: `paperfmt/cli.py` — 添加 `--list-rules` 标志和 markdown 渲染器
- Modify: `tests/test_cli.py` — 添加 `--list-rules` 测试
- Modify: `tests/test_workflow.py` — 添加 `--format markdown` 测试

- [ ] **Step 1: 为 RulePlugin 添加 description 字段**

```python
# paperfmt/core/rules/base.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from paperfmt.core.models import Diagnostic, RuleSet


@dataclass(slots=True)
class RulePlugin:
    rule_id: str
    description: str
    default_severity: str
    check: Callable[[str, Path, RuleSet], list[Diagnostic]]
    fix: Callable[[str], tuple[str, bool]] | None = None
```

- [ ] **Step 2: 运行现有测试确认 description 缺失导致失败**

Run: `python -m pytest -q`
Expected: 11 处 RulePlugin 构造报错（缺少 description 参数）

- [ ] **Step 3: 为所有现有 RulePlugin 添加 description**

```python
# paperfmt/core/rules/ieee_conf.py — 更新 RULES tuple 中每个 RulePlugin
RULES: tuple[RulePlugin, ...] = (
    RulePlugin("IEEE001", "Figure caption should be placed after includegraphics", "warning", lambda text, tex_file, ruleset: _check_figure_caption_order(text), _fix_rule_001),
    RulePlugin("IEEE002", "Table caption should be placed before tabular", "warning", lambda text, tex_file, ruleset: _check_table_caption_order(text), _fix_rule_002),
    RulePlugin("IEEE003", "Use \\cite for IEEE numeric citation style", "warning", lambda text, tex_file, ruleset: _check_citation_style(text), _fix_rule_003),
    RulePlugin("CITE-MANUAL", "Manual numeric citation [n] detected", "warning", lambda text, tex_file, ruleset: _check_manual_numeric_citations(text)),
    RulePlugin("REF-HARDCODE", "Hard-coded cross reference (Eq., Fig., Table)", "warning", lambda text, tex_file, ruleset: _check_hardcoded_cross_refs(text)),
    RulePlugin("TAB-FORMAT", "\\hline in table; prefer booktabs commands", "warning", lambda text, tex_file, ruleset: _check_table_format_booktabs(text)),
    RulePlugin("BIB-CROSSCHECK", "Cross-check citations against bibliography", "warning", lambda text, tex_file, ruleset: _check_bib_crosscheck(text, tex_file, ruleset.bibliography)),
    RulePlugin("IEEE004", "Missing abstract environment", "error", lambda text, tex_file, ruleset: [d for d in _check_required_sections(text) if d.rule_id == "IEEE004"]),
    RulePlugin("IEEE005", "Missing IEEEkeywords environment", "warning", lambda text, tex_file, ruleset: [d for d in _check_required_sections(text) if d.rule_id == "IEEE005"]),
    RulePlugin("IEEE006", "Possible anonymization leak in author block", "warning", lambda text, tex_file, ruleset: _check_anonymization_leak(text)),
    RulePlugin("IEEE007", "Cited entry missing DOI in bibliography", "warning", lambda text, tex_file, ruleset: _check_missing_doi_from_config(text, tex_file, ruleset.bibliography)),
)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest -q`
Expected: all tests pass

- [ ] **Step 5: 添加 `--list-rules` 到 check 命令**

```python
# paperfmt/cli.py — 在 check_command 函数开头（config 加载之后、tex_file 检查之前）添加:
@main.command("check")
@click.argument("tex_file", required=False, type=click.Path(dir_okay=False, path_type=Path))
@click.option("--template", "template_name", default=None, type=click.Choice(supported_templates()), help="Template override")
@click.option("--format", "output_format", default="text", type=click.Choice(["text", "json"]), show_default=True)
@click.option("--strict", is_flag=True, default=False, help="Return non-zero when warnings exist")
@click.option("--config", "config_path", default="paperfmt.toml", type=click.Path(dir_okay=False, path_type=Path), show_default=True)
@click.option("--list-rules", is_flag=True, default=False, help="List all rules for the template and exit")
def check_command(tex_file: Path | None, template_name: str | None, output_format: str, strict: bool, config_path: Path, list_rules: bool) -> None:
    """Scan .tex file for template compliance and formatting issues."""
    cfg = load_project_config(config_path)
    effective_template = template_name or cfg.template
    ruleset = default_ruleset(template=effective_template, bibliography=cfg.bibliography, rules=cfg.rules)

    if list_rules:
        _list_rules(effective_template, ruleset)
        return

    effective_tex_file = tex_file or Path(cfg.main_tex)
    # ... 后续逻辑不变
```

- [ ] **Step 6: 实现 `_list_rules` 函数**

在 `cli.py` 中（`_render_text_report` 之前）添加:

```python
def _list_rules(template: str, ruleset: RuleSet) -> None:
    """Print all rules for the template with enabled/severity status."""
    from paperfmt.core.rules import get_template_plugins

    plugins = get_template_plugins(template)
    if not plugins:
        click.echo(f"No rules defined for template '{template}'.")
        return

    click.echo(f"Rules for {template}:")
    for plugin in plugins:
        enabled = ruleset.is_enabled(plugin.rule_id)
        severity = ruleset.resolve_severity(plugin.rule_id, plugin.default_severity)
        status = "enabled " if enabled else "disabled"
        fixable = " (fixable)" if plugin.fix is not None else ""
        click.echo(f"  [{status}] {plugin.rule_id} ({severity}){fixable}")
        click.echo(f"          {plugin.description}")
```

- [ ] **Step 7: 更新 test_cli.py 添加 `--list-rules` 测试**

```python
# tests/test_cli.py
from click.testing import CliRunner

from paperfmt.cli import main


def test_cli_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "init" in result.output
    assert "check" in result.output
    assert "fix" in result.output


def test_check_list_rules() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "ieee-conf"])
        result = runner.invoke(main, ["check", "--list-rules"])
        assert result.exit_code == 0
        assert "IEEE001" in result.output
        assert "IEEE002" in result.output
        assert "IEEE003" in result.output
        assert "enabled" in result.output
        assert "warning" in result.output
```

- [ ] **Step 8: 运行测试确认通过**

Run: `python -m pytest tests/test_cli.py -v`
Expected: 2 tests pass

- [ ] **Step 9: 实现 `_render_markdown_report` 函数**

在 `cli.py` 中 `_render_text_report` 之后添加:

同时需要在 `paperfmt/core/models.py` 中给 `CheckReport` 添加 `template` 字段:

```python
@dataclass(slots=True)
class CheckReport:
    input_file: Path
    template: str
    diagnostics: list[Diagnostic]
```

以及在 `paperfmt/core/checker.py` 的 `run_checks()` 中更新 `CheckReport` 构造:

```python
    return CheckReport(input_file=tex_file, template=normalized_template, diagnostics=diagnostics)
```

```python
def _render_markdown_report(report: CheckReport) -> None:
    if not report.diagnostics:
        click.echo("**No issues found.**")
        return

    click.echo(f"## paperfmt Check Report")
    click.echo()
    click.echo(f"**Template:** {report.template}")
    click.echo(f"**File:** {report.input_file}")
    click.echo()
    click.echo("| Severity | Rule | Line | Message | Fixable |")
    click.echo("|----------|------|------|---------|---------|")
    for item in report.diagnostics:
        can_fix = "yes" if item.can_fix else "no"
        click.echo(f"| {item.severity.upper()} | {item.rule_id} | {item.line} | {item.message} | {can_fix} |")
    click.echo()
    click.echo(f"**Summary:** {len(report.diagnostics)} issues, {report.error_count} errors, {report.warning_count} warnings")
```

- [ ] **Step 10: 更新 check_command 支持 `--format markdown`**

在 `check_command` 的 `@click.option("--format"` 行中，将 choices 改为 `["text", "json", "markdown"]`。

在输出分支中（`if output_format == "json":` 之后），添加:

```python
    elif output_format == "markdown":
        _render_markdown_report(report)
```

同时更新 `_append_report` 调用，使 markdown 格式也写入报告文件。

- [ ] **Step 11: 更新 test_workflow.py 添加 markdown 格式测试**

```python
# tests/test_workflow.py — 在文件末尾添加:
def test_check_markdown_format() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "ieee-conf"])
        Path("main.tex").write_text(_problematic_tex(), encoding="utf-8")

        result = runner.invoke(main, ["check", "--format", "markdown"])
        assert result.exit_code == 0
        assert "## paperfmt Check Report" in result.output
        assert "| Severity | Rule | Line | Message | Fixable |" in result.output
        assert "IEEE001" in result.output
```

- [ ] **Step 12: 运行全部测试确认通过**

Run: `python -m pytest -q`
Expected: all tests pass

- [ ] **Step 13: Commit**

```bash
git add paperfmt/core/rules/base.py paperfmt/core/rules/ieee_conf.py paperfmt/core/models.py paperfmt/core/checker.py paperfmt/cli.py tests/test_cli.py tests/test_workflow.py
git commit -m "feat: add --list-rules, --format markdown, and RulePlugin.description"
```

---

### Task 2: 多文件项目支持 — `\input`/`\include` 递归解析

**Files:**
- Create: `paperfmt/core/tex_utils.py` — `resolve_includes()` 函数
- Modify: `paperfmt/core/checker.py` — 在 `run_checks()` 中使用 `resolve_includes()`
- Modify: `tests/test_workflow.py` — 多文件项目测试

- [ ] **Step 1: 创建 tex_utils.py 并编写测试先**

```python
# paperfmt/core/tex_utils.py
from __future__ import annotations

import re
from pathlib import Path

_INPUT_RE = re.compile(r"\\(?:input|include)\s*\{([^}]+)\}")


def resolve_includes(tex_file: Path, visited: set[Path] | None = None) -> str:
    """Recursively resolve \\input and \\include directives, returning combined text."""
    if visited is None:
        visited = set()

    tex_file = tex_file.resolve()
    if tex_file in visited:
        return f"% [paperfmt] circular include skipped: {tex_file}\n"
    visited.add(tex_file)

    base_dir = tex_file.parent
    text = tex_file.read_text(encoding="utf-8")

    def _replace(match: re.Match[str]) -> str:
        sub_name = match.group(1).strip()
        # LaTeX convention: \input{file} reads file.tex
        sub_path = base_dir / sub_name
        if not sub_path.suffix:
            sub_path = sub_path.with_suffix(".tex")
        if not sub_path.exists():
            return match.group(0)  # keep original if not found
        resolved = resolve_includes(sub_path, visited)
        return f"% [paperfmt] begin include: {sub_path.name}\n{resolved}% [paperfmt] end include\n"

    return _INPUT_RE.sub(_replace, text)
```

- [ ] **Step 2: 编写测试**

```python
# tests/test_workflow.py — 在文件末尾添加:
def test_resolve_includes_single_file() -> None:
    from paperfmt.core.tex_utils import resolve_includes

    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("main.tex").write_text("Hello\n\\input{sub}\nWorld\n", encoding="utf-8")
        Path("sub.tex").write_text("Included\n", encoding="utf-8")

        result = resolve_includes(Path("main.tex"))
        assert "Hello" in result
        assert "Included" in result
        assert "World" in result


def test_resolve_includes_nested() -> None:
    from paperfmt.core.tex_utils import resolve_includes

    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("main.tex").write_text("A\n\\input{sub}\nB\n", encoding="utf-8")
        Path("sub.tex").write_text("C\n\\input{deep}\nD\n", encoding="utf-8")
        Path("deep.tex").write_text("E\n", encoding="utf-8")

        result = resolve_includes(Path("main.tex"))
        assert "A" in result
        assert "C" in result
        assert "E" in result
        assert "D" in result
        assert "B" in result


def test_resolve_includes_missing_file() -> None:
    from paperfmt.core.tex_utils import resolve_includes

    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("main.tex").write_text("A\n\\input{missing}\nB\n", encoding="utf-8")

        result = resolve_includes(Path("main.tex"))
        assert "\\input{missing}" in result  # kept as-is
```

- [ ] **Step 3: 运行测试确认失败**

Run: `python -m pytest tests/test_workflow.py -k resolve -v`
Expected: 3 tests fail with "tex_utils not found" (if Step 1 file not yet created) or pass

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/test_workflow.py -k resolve -v`
Expected: 3 tests pass

- [ ] **Step 5: 更新 checker.py 使用 resolve_includes**

```python
# paperfmt/core/checker.py — 修改 run_checks() 函数:
from paperfmt.core.tex_utils import resolve_includes

def run_checks(tex_file: Path, template: str, ruleset: RuleSet | None = None) -> CheckReport:
    normalized_template = normalize_template(template)
    if not is_supported_template(normalized_template):
        raise ValueError(f"Unsupported template: {template}")

    active_ruleset = ruleset or default_ruleset(template=normalized_template)
    text = resolve_includes(tex_file)
    diagnostics: list[Diagnostic] = []

    for plugin in get_template_plugins(normalized_template):
        if not active_ruleset.is_enabled(plugin.rule_id):
            continue
        rule_diagnostics = plugin.check(text, tex_file, active_ruleset)
        resolved = active_ruleset.resolve_severity(plugin.rule_id, plugin.default_severity)
        for item in rule_diagnostics:
            diagnostics.append(
                Diagnostic(
                    rule_id=item.rule_id,
                    severity=resolved,
                    message=item.message,
                    line=item.line,
                    can_fix=item.can_fix,
                )
            )

    diagnostics.sort(key=lambda d: (d.line, d.rule_id))
    return CheckReport(input_file=tex_file, diagnostics=diagnostics)
```

关键改动：将 `text = tex_file.read_text(encoding="utf-8")` 替换为 `text = resolve_includes(tex_file)`。

- [ ] **Step 6: 编写多文件项目工作流测试**

```python
# tests/test_workflow.py — 添加:
def test_check_multi_file_project() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "ieee-conf"])
        Path("main.tex").write_text(
            """\\documentclass[conference]{IEEEtran}
\\title{Demo}
\\author{Anonymous}
\\begin{document}
\\maketitle
\\begin{abstract}
Demo.
\\end{abstract}
\\begin{IEEEkeywords}
demo
\\end{IEEEkeywords}
\\input{section1}
\\end{document}
""",
            encoding="utf-8",
        )
        Path("section1.tex").write_text(
            """\\begin{figure}
\\caption{A figure}
\\includegraphics{demo.png}
\\end{figure}
See \\citep{demo2026}.
""",
            encoding="utf-8",
        )

        result = runner.invoke(main, ["check"])
        assert result.exit_code == 0
        # IEEE001 (caption before image) should be detected in section1.tex
        assert "IEEE001" in result.output
        # IEEE003 (citep) should be detected in section1.tex
        assert "IEEE003" in result.output
```

- [ ] **Step 7: 运行全部测试确认通过**

Run: `python -m pytest -q`
Expected: all tests pass

- [ ] **Step 8: Commit**

```bash
git add paperfmt/core/tex_utils.py paperfmt/core/checker.py tests/test_workflow.py
git commit -m "feat: add multi-file project support via \\input/\\include resolution"
```

---

### Task 3: 结构规则 — IEEE008, IEEE011(fix), IEEE012

**Files:**
- Modify: `paperfmt/core/rules/ieee_conf.py` — 新增 3 个检查函数 + 1 个修复函数 + 3 个 RulePlugin
- Modify: `tests/test_workflow.py` — 新增结构规则测试

- [ ] **Step 1: 编写测试**

```python
# tests/test_workflow.py — 添加:
def test_check_ieee008_missing_thanks() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "ieee-conf"])
        # No \thanks in author block
        Path("main.tex").write_text(
            """\\documentclass[conference]{IEEEtran}
\\title{Demo}
\\author{John Doe}
\\begin{document}
\\maketitle
\\begin{abstract}
Demo.
\\end{abstract}
\\begin{IEEEkeywords}
demo
\\end{IEEEkeywords}
\\end{document}
""",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["check"])
        assert result.exit_code == 0
        # IEEE008 warns when no \thanks or \IEEEPARstart
        assert "IEEE008" in result.output


def test_check_ieee011_missing_bibliographystyle() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "ieee-conf"])
        Path("main.tex").write_text(
            """\\documentclass[conference]{IEEEtran}
\\title{Demo}
\\author{Anonymous}
\\begin{document}
\\maketitle
\\begin{abstract}
Demo.
\\end{abstract}
\\begin{IEEEkeywords}
demo
\\end{IEEEkeywords}
\\bibliography{references}
\\end{document}
""",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["check"])
        assert result.exit_code != 0  # error severity
        assert "IEEE011" in result.output


def test_fix_ieee011_adds_bibliographystyle() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "ieee-conf"])
        tex = Path("main.tex")
        content = """\\documentclass[conference]{IEEEtran}
\\title{Demo}
\\author{Anonymous}
\\begin{document}
\\maketitle
\\begin{abstract}
Demo.
\\end{abstract}
\\begin{IEEEkeywords}
demo
\\end{IEEEkeywords}
\\bibliography{references}
\\end{document}
"""
        tex.write_text(content, encoding="utf-8")
        result = runner.invoke(main, ["fix"])
        assert result.exit_code == 0
        updated = tex.read_text(encoding="utf-8")
        assert "\\bibliographystyle{IEEEtran}" in updated
        # bibliographystyle should appear before bibliography
        bs_pos = updated.index("\\bibliographystyle{IEEEtran}")
        bib_pos = updated.index("\\bibliography{references}")
        assert bs_pos < bib_pos


def test_check_ieee012_missing_balance() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "ieee-conf"])
        Path("main.tex").write_text(
            """\\documentclass[conference]{IEEEtran}
\\title{Demo}
\\author{Anonymous}
\\begin{document}
\\maketitle
\\begin{abstract}
Demo.
\\end{abstract}
\\begin{IEEEkeywords}
demo
\\end{IEEEkeywords}
\\bibliographystyle{IEEEtran}
\\bibliography{references}
\\end{document}
""",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["check"])
        assert result.exit_code == 0
        # IEEE012 warns when no balancing command between bibliography and end document
        assert "IEEE012" in result.output
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_workflow.py -k "ieee008 or ieee011 or ieee012" -v`
Expected: 4 tests FAIL (IEEE008/IEEE011/IEEE012 not yet implemented)

- [ ] **Step 3: 实现检查函数**

在 `paperfmt/core/rules/ieee_conf.py` 中添加（`_check_anonymization_leak` 函数之后）:

```python
# IEEE008 helper regex
BIBLIOGRAPHY_CMD_RE = re.compile(r"\\bibliography\s*\{([^}]+)\}")
BIB_STYLE_RE = re.compile(r"\\bibliographystyle\s*\{([^}]+)\}")
PARSTART_RE = re.compile(r"\\IEEEPARstart")
BALANCE_RE = re.compile(r"\\(?:balance|balancest?authors|IEEEtriggeratref|IEEEtriggercmd)\b")


def _check_ieee_structure(text: str) -> list[Diagnostic]:
    """Run IEEE008, IEEE011, IEEE012 checks, returning all diagnostics."""
    diagnostics: list[Diagnostic] = []

    # IEEE008: check for \thanks in author block, \IEEEPARstart after \maketitle
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
```

- [ ] **Step 4: 实现 IEEE011 修复函数**

在 `ieee_conf.py` 中的 `_fix_rule_003` 之后添加:

```python
def _fix_rule_011(text: str) -> tuple[str, bool]:
    """Insert \\bibliographystyle{IEEEtran} before \\bibliography."""
    bib_match = BIBLIOGRAPHY_CMD_RE.search(text)
    if not bib_match:
        return text, False
    # Only insert if not already present
    if BIB_STYLE_RE.search(text):
        return text, False
    insert_pos = bib_match.start()
    updated = text[:insert_pos] + "\\bibliographystyle{IEEEtran}\n" + text[insert_pos:]
    return updated, True
```

- [ ] **Step 5: 更新 RULES tuple**

在 `ieee_conf.py` 的 `RULES` tuple 末尾（`IEEE007` 行之后，`)` 之前）添加:

```python
    RulePlugin("IEEE008", "Check for \\thanks and \\IEEEPARstart presence", "warning", lambda text, tex_file, ruleset: [d for d in _check_ieee_structure(text) if d.rule_id == "IEEE008"]),
    RulePlugin("IEEE011", "Check for missing \\bibliographystyle{IEEEtran}", "error", lambda text, tex_file, ruleset: [d for d in _check_ieee_structure(text) if d.rule_id == "IEEE011"], _fix_rule_011),
    RulePlugin("IEEE012", "Check for missing column balance command", "info", lambda text, tex_file, ruleset: [d for d in _check_ieee_structure(text) if d.rule_id == "IEEE012"]),
```

- [ ] **Step 6: 运行新规则测试确认通过**

Run: `python -m pytest tests/test_workflow.py -k "ieee008 or ieee011 or ieee012" -v`
Expected: 4 tests PASS

- [ ] **Step 7: 运行全部测试确认没有回归**

Run: `python -m pytest -q`
Expected: all tests pass

- [ ] **Step 8: Commit**

```bash
git add paperfmt/core/rules/ieee_conf.py tests/test_workflow.py
git commit -m "feat: add IEEE008, IEEE011(fix), IEEE012 structural rules"
```

---

### Task 4: 引用/格式规则 — IEEE009(fix), IEEE010

**Files:**
- Modify: `paperfmt/core/rules/ieee_conf.py` — 新增检查 + 修复函数 + 2 个 RulePlugin
- Modify: `tests/test_workflow.py` — 新增测试

- [ ] **Step 1: 编写测试**

```python
# tests/test_workflow.py — 添加:
def test_check_ieee009_cite_separator() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "ieee-conf"])
        Path("main.tex").write_text(
            """\\documentclass[conference]{IEEEtran}
\\title{Demo}
\\author{Anonymous}
\\begin{document}
\\maketitle
\\begin{abstract}
Demo.
\\end{abstract}
\\begin{IEEEkeywords}
demo
\\end{IEEEkeywords}
See \\cite{key1 key2 key3}.
\\end{document}
""",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["check"])
        assert result.exit_code == 0
        assert "IEEE009" in result.output


def test_fix_ieee009_cite_separator() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "ieee-conf"])
        tex = Path("main.tex")
        tex.write_text(
            """\\documentclass[conference]{IEEEtran}
\\title{Demo}
\\author{Anonymous}
\\begin{document}
\\maketitle
\\begin{abstract}
Demo.
\\end{abstract}
\\begin{IEEEkeywords}
demo
\\end{IEEEkeywords}
See \\cite{key1 key2 key3}.
\\end{document}
""",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["fix"])
        assert result.exit_code == 0
        updated = tex.read_text(encoding="utf-8")
        assert "\\cite{key1, key2, key3}" in updated


def test_check_ieee010_equation_punctuation() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "ieee-conf"])
        Path("main.tex").write_text(
            """\\documentclass[conference]{IEEEtran}
\\title{Demo}
\\author{Anonymous}
\\begin{document}
\\maketitle
\\begin{abstract}
Demo.
\\end{abstract}
\\begin{IEEEkeywords}
demo
\\end{IEEEkeywords}
\\begin{equation}
E = mc^2
\\end{equation}
\\end{document}
""",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["check"])
        assert result.exit_code == 0
        assert "IEEE010" in result.output
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_workflow.py -k "ieee009 or ieee010" -v`
Expected: 3 tests FAIL

- [ ] **Step 3: 实现检查函数**

在 `ieee_conf.py` 中添加:

```python
# IEEE009: cite keys separated by space instead of comma
CITE_SPACE_SEP_RE = re.compile(r"\\cite\s*\{([^}]+)\}")


def _check_cite_separator(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for match in CITE_SPACE_SEP_RE.finditer(text):
        keys_text = match.group(1).strip()
        if not keys_text:
            continue
        parts = [k.strip() for k in keys_text.split(",")]
        # Check if any part contains spaces (suggesting space-separated keys)
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
                break  # one diagnostic per cite command
    return diagnostics


# IEEE010: equation lacks trailing punctuation
EQ_ENV_RE = re.compile(r"\\begin\{equation\*?\}(.*?)\\end\{equation\*?\}", re.DOTALL)
EQ_PUNCT_RE = re.compile(r"[.,;:!?]\s*$")


def _check_equation_punctuation(text: str) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for match in EQ_ENV_RE.finditer(text):
        body = match.group(1).rstrip()
        # Remove \label{...} from the end to check what precedes it
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
```

- [ ] **Step 4: 实现 IEEE009 修复函数**

```python
def _fix_rule_009(text: str) -> tuple[str, bool]:
    """Replace space-separated cite keys with comma-separated."""

    def _fix_cite(match: re.Match[str]) -> str:
        keys_text = match.group(1)
        keys = [k.strip() for k in keys_text.replace(",", " ").split()]
        return "\\cite{" + ", ".join(keys) + "}"

    updated = CITE_SPACE_SEP_RE.sub(_fix_cite, text)
    return updated, updated != text
```

- [ ] **Step 5: 更新 RULES tuple**

在 `RULES` tuple 中 `IEEE007` 行之后添加:

```python
    RulePlugin("IEEE009", "\\cite keys should be comma-separated", "warning", lambda text, tex_file, ruleset: _check_cite_separator(text), _fix_rule_009),
    RulePlugin("IEEE010", "Equation should end with punctuation", "warning", lambda text, tex_file, ruleset: _check_equation_punctuation(text)),
```

- [ ] **Step 6: 运行新测试确认通过**

Run: `python -m pytest tests/test_workflow.py -k "ieee009 or ieee010" -v`
Expected: 3 tests PASS

- [ ] **Step 7: 运行全部测试确认没有回归**

Run: `python -m pytest -q`
Expected: all tests pass

- [ ] **Step 8: Commit**

```bash
git add paperfmt/core/rules/ieee_conf.py tests/test_workflow.py
git commit -m "feat: add IEEE009(fix) cite separator and IEEE010 equation punctuation rules"
```

---

### Task 5: 交叉引用规则 — FIG-REF, TAB-REF, EQ-REF

**Files:**
- Modify: `paperfmt/core/rules/ieee_conf.py` — 新增检查函数 + 3 个 RulePlugin
- Modify: `tests/test_workflow.py` — 新增测试

- [ ] **Step 1: 编写测试**

```python
# tests/test_workflow.py — 添加:
def test_check_fig_ref_unreferenced() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "ieee-conf"])
        Path("main.tex").write_text(
            """\\documentclass[conference]{IEEEtran}
\\title{Demo}
\\author{Anonymous}
\\begin{document}
\\maketitle
\\begin{abstract}
Demo.
\\end{abstract}
\\begin{IEEEkeywords}
demo
\\end{IEEEkeywords}
\\begin{figure}
\\includegraphics{demo.png}
\\caption{A figure}
\\label{fig:demo}
\\end{figure}
\\end{document}
""",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["check"])
        assert result.exit_code == 0
        assert "FIG-REF" in result.output


def test_check_fig_ref_referenced_no_warning() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "ieee-conf"])
        Path("main.tex").write_text(
            """\\documentclass[conference]{IEEEtran}
\\title{Demo}
\\author{Anonymous}
\\begin{document}
\\maketitle
\\begin{abstract}
Demo.
\\end{abstract}
\\begin{IEEEkeywords}
demo
\\end{IEEEkeywords}
\\begin{figure}
\\includegraphics{demo.png}
\\caption{A figure}
\\label{fig:demo}
\\end{figure}
See Fig.~\\ref{fig:demo}.
\\end{document}
""",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["check"])
        assert result.exit_code == 0
        assert "FIG-REF" not in result.output


def test_check_eq_ref_unreferenced() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "ieee-conf"])
        Path("main.tex").write_text(
            """\\documentclass[conference]{IEEEtran}
\\title{Demo}
\\author{Anonymous}
\\begin{document}
\\maketitle
\\begin{abstract}
Demo.
\\end{abstract}
\\begin{IEEEkeywords}
demo
\\end{IEEEkeywords}
\\begin{equation}
E = mc^2
\\label{eq:energy}
\\end{equation}
\\end{document}
""",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["check"])
        assert result.exit_code == 0
        assert "EQ-REF" in result.output


def test_check_tab_ref_unreferenced() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "ieee-conf"])
        Path("main.tex").write_text(
            """\\documentclass[conference]{IEEEtran}
\\title{Demo}
\\author{Anonymous}
\\begin{document}
\\maketitle
\\begin{abstract}
Demo.
\\end{abstract}
\\begin{IEEEkeywords}
demo
\\end{IEEEkeywords}
\\begin{table}
\\caption{Results}
\\label{tab:results}
\\begin{tabular}{c}
A \\\\
\\end{tabular}
\\end{table}
\\end{document}
""",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["check"])
        assert result.exit_code == 0
        assert "TAB-REF" in result.output
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_workflow.py -k "fig_ref or eq_ref or tab_ref" -v`
Expected: 4 tests FAIL

- [ ] **Step 3: 实现检查函数**

在 `ieee_conf.py` 中添加:

```python
# Cross-reference rules: FIG-REF, TAB-REF, EQ-REF
LABEL_IN_ENV_RE = re.compile(
    r"\\(?:begin)\{(figure|table|equation)\*?\}(.*?)\\end\{\1\*?\}",
    re.DOTALL,
)
LABEL_RE = re.compile(r"\\label\{([^}]+)\}")
REF_RE = re.compile(r"\\(?:ref|eqref)\{([^}]+)\}")


def _check_unreferenced_labels(text: str) -> list[Diagnostic]:
    """Check that labels inside figure/table/equation are referenced in text."""
    diagnostics: list[Diagnostic] = []
    env_type_map = {"figure": "FIG-REF", "table": "TAB-REF", "equation": "EQ-REF"}
    env_names = {"figure": "Figure", "table": "Table", "equation": "Equation"}

    # Collect all labels inside environments
    for env_match in LABEL_IN_ENV_RE.finditer(text):
        env_type = env_match.group(1)
        if env_type not in env_type_map:
            continue
        env_body = env_match.group(2)
        for label_match in LABEL_RE.finditer(env_body):
            label = label_match.group(1).strip()
            # Check if this label is referenced OUTSIDE the environment
            outside_text = text[: env_match.start()] + text[env_match.end() :]
            ref_pattern = re.compile(
                r"\\(?:ref|eqref)\{" + re.escape(label) + r"\}"
            )
            if not ref_pattern.search(outside_text):
                diagnostics.append(
                    Diagnostic(
                        rule_id=env_type_map[env_type],
                        severity="warning",
                        message=f"{env_names[env_type]} label '{label}' is not referenced in text.",
                        line=_line_of_offset(text, label_match.start()),
                    )
                )
    return diagnostics
```

- [ ] **Step 4: 更新 RULES tuple**

在 `RULES` tuple 末尾添加:

```python
    RulePlugin("FIG-REF", "Check that figure labels are referenced in text", "warning", lambda text, tex_file, ruleset: [d for d in _check_unreferenced_labels(text) if d.rule_id == "FIG-REF"]),
    RulePlugin("TAB-REF", "Check that table labels are referenced in text", "warning", lambda text, tex_file, ruleset: [d for d in _check_unreferenced_labels(text) if d.rule_id == "TAB-REF"]),
    RulePlugin("EQ-REF", "Check that equation labels are referenced in text", "warning", lambda text, tex_file, ruleset: [d for d in _check_unreferenced_labels(text) if d.rule_id == "EQ-REF"]),
```

- [ ] **Step 5: 运行新测试确认通过**

Run: `python -m pytest tests/test_workflow.py -k "fig_ref or eq_ref or tab_ref" -v`
Expected: 4 tests PASS

- [ ] **Step 6: 运行全部测试确认没有回归**

Run: `python -m pytest -q`
Expected: all tests pass

- [ ] **Step 7: Commit**

```bash
git add paperfmt/core/rules/ieee_conf.py tests/test_workflow.py
git commit -m "feat: add FIG-REF, TAB-REF, EQ-REF cross-reference validation rules"
```

---

### Task 6: 外部资源检查 — IMG-RES, LINK-VALID

**Files:**
- Modify: `paperfmt/core/rules/ieee_conf.py` — 新增检查函数 + 2 个 RulePlugin
- Modify: `pyproject.toml` — 添加可选依赖 `[project.optional-dependencies]`
- Modify: `tests/test_workflow.py` — 新增测试

- [ ] **Step 1: 添加可选依赖到 pyproject.toml**

```toml
# pyproject.toml — 在 [project.optional-dependencies] 中更新:
[project.optional-dependencies]
dev = [
  "pytest>=8.2.0"
]
image = [
  "Pillow>=10.0"
]
link = [
  "httpx>=0.27"
]
full = [
  "paperfmt[image,link]"
]
```

- [ ] **Step 2: 编写测试**

```python
# tests/test_workflow.py — 添加:
def test_check_img_res_skips_without_pillow(monkeypatch) -> None:
    """IMG-RES should be skipped (no diagnostic) when Pillow is not installed."""
    import builtins
    original_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "PIL" or name.startswith("PIL."):
            raise ImportError("No PIL")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)

    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "ieee-conf"])
        Path("main.tex").write_text(
            """\\documentclass[conference]{IEEEtran}
\\title{Demo}
\\author{Anonymous}
\\begin{document}
\\maketitle
\\begin{abstract}
Demo.
\\end{abstract}
\\begin{IEEEkeywords}
demo
\\end{IEEEkeywords}
\\begin{figure}
\\includegraphics{demo.png}
\\caption{A figure}
\\end{figure}
\\end{document}
""",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["check"])
        assert result.exit_code == 0
        # IMG-RES should not produce diagnostic when PIL is missing
        assert "IMG-RES" not in result.output


def test_check_link_valid_skips_without_httpx(monkeypatch) -> None:
    """LINK-VALID should be skipped when httpx is not installed."""
    import builtins
    original_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "httpx":
            raise ImportError("No httpx")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)

    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "ieee-conf"])
        Path("main.tex").write_text(
            """\\documentclass[conference]{IEEEtran}
\\title{Demo}
\\author{Anonymous}
\\begin{document}
\\maketitle
\\begin{abstract}
Demo.
\\end{abstract}
\\begin{IEEEkeywords}
demo
\\end{IEEEkeywords}
See \\url{https://example.com}.
\\end{document}
""",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["check"])
        assert result.exit_code == 0
        assert "LINK-VALID" not in result.output
```

- [ ] **Step 3: 运行测试确认失败**

Run: `python -m pytest tests/test_workflow.py -k "img_res or link_valid" -v`
Expected: 2 tests FAIL

- [ ] **Step 4: 实现检查函数**

在 `ieee_conf.py` 中添加:

```python
# IMG-RES and LINK-VALID (optional dependencies)
INCLUDEGRAPHICS_RE = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\s*\{([^}]+)\}")
URL_CMD_RE = re.compile(r"\\(?:url|href)\{([^}]+)\}")


def _check_image_resolution(text: str, tex_file: Path) -> list[Diagnostic]:
    """Check that included images meet minimum resolution for print."""
    try:
        from PIL import Image  # type: ignore[import-untyped]
    except ImportError:
        return []  # skip if Pillow not available

    diagnostics: list[Diagnostic] = []
    base_dir = tex_file.parent.resolve()

    for match in INCLUDEGRAPHICS_RE.finditer(text):
        img_name = match.group(1).strip()
        img_path = base_dir / img_name
        if not img_path.exists():
            continue
        try:
            with Image.open(img_path) as img:
                width_px, height_px = img.size
            # For IEEE print: ~300 DPI recommended. Warning if < 150 DPI equivalent
            # Assume a typical column width of ~3.5 inches
            col_width_inches = 3.5
            dpi_est = width_px / col_width_inches
            if dpi_est < 150:
                diagnostics.append(
                    Diagnostic(
                        rule_id="IMG-RES",
                        severity="warning",
                        message=f"Image '{img_name}' resolution is low (~{dpi_est:.0f} DPI at column width). Consider using 300 DPI for print.",
                        line=_line_of_offset(text, match.start()),
                    )
                )
        except Exception:
            continue  # skip unreadable images
    return diagnostics


def _check_link_validity(text: str) -> list[Diagnostic]:
    """Check that URLs/DOIs are accessible (best-effort HEAD request)."""
    try:
        import httpx
    except ImportError:
        return []  # skip if httpx not available

    diagnostics: list[Diagnostic] = []
    for match in URL_CMD_RE.finditer(text):
        url = match.group(1).strip()
        # Resolve DOI shorthand
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
                        line=_line_of_offset(text, match.start()),
                    )
                )
        except Exception:
            diagnostics.append(
                Diagnostic(
                    rule_id="LINK-VALID",
                    severity="warning",
                    message=f"URL '{url[:60]}...' is unreachable.",
                    line=_line_of_offset(text, match.start()),
                )
            )
    return diagnostics
```

- [ ] **Step 5: 更新 RULES tuple**

在 `RULES` tuple 末尾添加:

```python
    RulePlugin("IMG-RES", "Check included image resolution for print quality", "warning", lambda text, tex_file, ruleset: _check_image_resolution(text, tex_file)),
    RulePlugin("LINK-VALID", "Check URL/DOI accessibility", "warning", lambda text, tex_file, ruleset: _check_link_validity(text)),
```

- [ ] **Step 6: 安装可选依赖**

Run: `pip install -e ".[image,link]"`

- [ ] **Step 7: 运行新测试确认通过**

Run: `python -m pytest tests/test_workflow.py -k "img_res or link_valid" -v`
Expected: 2 tests PASS

- [ ] **Step 8: 运行全部测试确认没有回归**

Run: `python -m pytest -q`
Expected: all tests pass

- [ ] **Step 9: Commit**

```bash
git add paperfmt/core/rules/ieee_conf.py tests/test_workflow.py pyproject.toml
git commit -m "feat: add IMG-RES image resolution and LINK-VALID URL accessibility rules"
```

---

### Task 7: 启发式检查 — PAGE-LIMIT, SEC-DEPTH

**Files:**
- Modify: `paperfmt/core/rules/ieee_conf.py` — 新增检查函数 + 2 个 RulePlugin
- Modify: `tests/test_workflow.py` — 新增测试

- [ ] **Step 1: 编写测试**

```python
# tests/test_workflow.py — 添加:
def test_check_sec_depth() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "ieee-conf"])
        # Use subsubsection (3 levels deep) which triggers SEC-DEPTH
        Path("main.tex").write_text(
            """\\documentclass[conference]{IEEEtran}
\\title{Demo}
\\author{Anonymous}
\\begin{document}
\\maketitle
\\begin{abstract}
Demo.
\\end{abstract}
\\begin{IEEEkeywords}
demo
\\end{IEEEkeywords}
\\section{Intro}
\\subsection{Background}
\\subsubsection{Details}
\\end{document}
""",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["check"])
        assert result.exit_code == 0
        assert "SEC-DEPTH" in result.output


def test_check_page_limit() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "ieee-conf"])
        # Make a long document to trigger PAGE-LIMIT
        long_content = (
            "\\documentclass[conference]{IEEEtran}\n"
            "\\title{Demo}\n"
            "\\author{Anonymous}\n"
            "\\begin{document}\n"
            "\\maketitle\n"
            "\\begin{abstract}\nDemo.\n\\end{abstract}\n"
            "\\begin{IEEEkeywords}\ndemo\n\\end{IEEEkeywords}\n"
        )
        # Add enough lines to suggest > 6 pages
        long_content += "A paragraph of text. " * 500 + "\n"
        long_content += "\\end{document}\n"

        Path("main.tex").write_text(long_content, encoding="utf-8")
        result = runner.invoke(main, ["check"])
        assert result.exit_code == 0
        assert "PAGE-LIMIT" in result.output
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_workflow.py -k "sec_depth or page_limit" -v`
Expected: 2 tests FAIL

- [ ] **Step 3: 实现检查函数**

在 `ieee_conf.py` 中添加:

```python
# PAGE-LIMIT and SEC-DEPTH
SECTION_DEPTH_RE = re.compile(r"\\(section|subsection|subsubsection|paragraph)\s*\{")
SUBSECTION_RE = re.compile(r"\\subsubsection\s*\{")


def _check_section_depth(text: str) -> list[Diagnostic]:
    """Warn if section nesting goes too deep (past subsection)."""
    diagnostics: list[Diagnostic] = []
    for match in SUBSECTION_RE.finditer(text):
        diagnostics.append(
            Diagnostic(
                rule_id="SEC-DEPTH",
                severity="info",
                message="Deep section nesting (subsubsection) detected; consider flattening for conference papers.",
                line=_line_of_offset(text, match.start()),
            )
        )
    return diagnostics


def _check_page_limit(text: str) -> list[Diagnostic]:
    """Estimate if document exceeds typical IEEE conference page limit (~6 pages)."""
    diagnostics: list[Diagnostic] = []
    lines = text.splitlines()
    # Rough heuristic: ~40 lines per page for two-column IEEE format
    estimated_pages = len(lines) / 40.0
    if estimated_pages > 8:
        diagnostics.append(
            Diagnostic(
                rule_id="PAGE-LIMIT",
                severity="warning",
                message=f"Draft may exceed page limit (~{estimated_pages:.0f} pages estimated). IEEE conferences typically allow 6-8 pages.",
                line=1,
            )
        )
    return diagnostics
```

- [ ] **Step 4: 更新 RULES tuple**

在 `RULES` tuple 末尾添加:

```python
    RulePlugin("PAGE-LIMIT", "Estimate page count against conference limits", "warning", lambda text, tex_file, ruleset: _check_page_limit(text)),
    RulePlugin("SEC-DEPTH", "Check section nesting depth", "info", lambda text, tex_file, ruleset: _check_section_depth(text)),
```

- [ ] **Step 5: 运行新测试确认通过**

Run: `python -m pytest tests/test_workflow.py -k "sec_depth or page_limit" -v`
Expected: 2 tests PASS

- [ ] **Step 6: 运行全部测试确认没有回归**

Run: `python -m pytest -q`
Expected: all tests pass

- [ ] **Step 7: Commit**

```bash
git add paperfmt/core/rules/ieee_conf.py tests/test_workflow.py
git commit -m "feat: add PAGE-LIMIT and SEC-DEPTH heuristic check rules"
```

---

### Task 8: BIB-CROSSCHECK `--prune-unused` 扩展

**Files:**
- Modify: `paperfmt/core/rules/ieee_conf.py` — 新增 `_prune_unused_bib_entries()` 函数
- Modify: `paperfmt/core/checker.py` — `apply_safe_fixes()` 支持返回 bib 修改
- Modify: `paperfmt/cli.py` — `fix_command` 添加 `--prune-unused` 标志
- Modify: `tests/test_workflow.py` — 新增 prune 测试

- [ ] **Step 1: 编写测试**

```python
# tests/test_workflow.py — 添加:
def test_fix_prune_unused() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "ieee-conf"])
        tex = Path("main.tex")
        bib = Path("references.bib")

        tex.write_text(
            """\\documentclass[conference]{IEEEtran}
\\title{Demo}
\\author{Anonymous}
\\begin{document}
\\maketitle
\\begin{abstract}
Demo.
\\end{abstract}
\\begin{IEEEkeywords}
demo
\\end{IEEEkeywords}
See \\cite{used_ref}.
\\bibliography{references}
\\end{document}
""",
            encoding="utf-8",
        )
        bib.write_text(
            """@article{used_ref,
  author = {Alice},
  title = {Used},
  journal = {Demo},
  year = {2024}
}

@article{unused_ref,
  author = {Bob},
  title = {Unused},
  journal = {Demo},
  year = {2024}
}
""",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["fix", "--prune-unused"])
        assert result.exit_code == 0
        updated_bib = bib.read_text(encoding="utf-8")
        assert "used_ref" in updated_bib
        assert "unused_ref" not in updated_bib
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_workflow.py -k prune -v`
Expected: test fails (Error: no such option: --prune-unused)

- [ ] **Step 3: 实现 bib prune 函数**

在 `ieee_conf.py` 末尾添加:

```python
def prune_unused_bib_entries(tex_text: str, bib_text: str) -> tuple[str, bool]:
    """Remove bibliography entries not cited in the tex file."""
    cited_keys = _extract_cited_keys(tex_text)
    if not cited_keys:
        return bib_text, False

    # Split bib entries using @ as delimiter
    entries = re.split(r"(?=@[a-zA-Z]+\s*\{)", bib_text)
    kept_entries: list[str] = []

    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue
        key_match = BIB_ENTRY_KEY_RE.match(entry)
        if key_match and key_match.group(1).strip() not in cited_keys:
            continue  # skip unused entry
        kept_entries.append(entry)

    result = "\n\n".join(kept_entries) + "\n"
    return result, result != bib_text
```

- [ ] **Step 4: 更新 fix_command 添加 --prune-unused 标志**

```python
# paperfmt/cli.py — fix_command 添加参数:
@click.option("--prune-unused", is_flag=True, default=False, help="Remove uncited bibliography entries")
def fix_command(tex_file: Path | None, template_name: str | None, dry_run: bool, backup: bool, config_path: Path, prune_unused: bool) -> None:
```

在 `fix_command` 中，`apply_safe_fixes` 之后添加 bib prune 逻辑:

```python
    if prune_unused:
        bib_path = (effective_tex_file.parent / cfg.bibliography).resolve()
        if bib_path.exists():
            from paperfmt.core.rules.ieee_conf import prune_unused_bib_entries
            bib_text = bib_path.read_text(encoding="utf-8")
            pruned_text, bib_changed = prune_unused_bib_entries(
                resolve_includes(effective_tex_file), bib_text
            )
            if bib_changed:
                if dry_run:
                    diff = "\n".join(
                        difflib.unified_diff(
                            bib_text.splitlines(),
                            pruned_text.splitlines(),
                            fromfile=f"{bib_path}",
                            tofile=f"{bib_path} (pruned)",
                            lineterm="",
                        )
                    )
                    click.echo(diff)
                    click.echo(f"Would prune unused entries from: {bib_path}")
                else:
                    if backup:
                        backup_bib = state_dir / "backup" / f"{bib_path.name}.bak"
                        backup_bib.write_text(bib_text, encoding="utf-8")
                        click.echo(f"Backup created: {backup_bib}")
                    bib_path.write_text(pruned_text, encoding="utf-8")
                    click.echo(f"Pruned unused entries from: {bib_path}")
```

同时需要在 `cli.py` 顶部添加 import:

```python
from paperfmt.core.tex_utils import resolve_includes
```

- [ ] **Step 5: 运行 prune 测试确认通过**

Run: `python -m pytest tests/test_workflow.py -k prune -v`
Expected: PASS

- [ ] **Step 6: 运行全部测试确认没有回归**

Run: `python -m pytest -q`
Expected: all tests pass

- [ ] **Step 7: 更新 test_cli.py 确保 --help 显示新选项**

Run: `python -m pytest tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add paperfmt/core/rules/ieee_conf.py paperfmt/core/checker.py paperfmt/cli.py tests/test_workflow.py
git commit -m "feat: add --prune-unused flag for removing uncited bibliography entries"
```

---

## Plan Summary

| Task | Description | New Rules | Est. Commits |
|------|-------------|-----------|-------------|
| 1 | CLI: `--format markdown` + `--list-rules` + description | — | 1 |
| 2 | Multi-file `\input`/`\include` resolution | — | 1 |
| 3 | Structural: IEEE008, IEEE011(fix), IEEE012 | 3 | 1 |
| 4 | Citation: IEEE009(fix), IEEE010 | 2 | 1 |
| 5 | Cross-reference: FIG-REF, TAB-REF, EQ-REF | 3 | 1 |
| 6 | External: IMG-RES, LINK-VALID | 2 | 1 |
| 7 | Heuristic: PAGE-LIMIT, SEC-DEPTH | 2 | 1 |
| 8 | BIB-CROSSCHECK `--prune-unused` | — | 1 |

**Final state:** 23 rules total (11 existing + 12 new), 6 auto-fixes (3 existing + 3 new), multi-file support, markdown reports.
