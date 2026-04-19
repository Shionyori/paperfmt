from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from paperfmt.cli import main


def _problematic_tex() -> str:
    return """\\documentclass[conference]{IEEEtran}
\\usepackage{graphicx}
\\title{Demo}
\\author{Anonymous}
\\begin{document}
\\maketitle
\\begin{abstract}
Demo abstract.
\\end{abstract}
\\begin{IEEEkeywords}
paperfmt, ieee
\\end{IEEEkeywords}

\\begin{figure}
\\caption{A figure caption}
\\includegraphics[width=0.4\\linewidth]{demo.png}
\\end{figure}

See \\citep{demo2026}.

\\begin{table}
\\begin{tabular}{c}
A
\\end{tabular}
\\caption{A table caption}
\\end{table}

\\end{document}
"""


def test_init_creates_files() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["init", "--template", "ieee"])
        assert result.exit_code == 0
        assert Path("main.tex").exists()
        assert Path("refs.bib").exists()


def test_check_reports_findings() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("main.tex").write_text(_problematic_tex(), encoding="utf-8")

        result = runner.invoke(main, ["check", "main.tex", "--template", "ieee"])
        assert result.exit_code == 0
        assert "IEEE001" in result.output
        assert "IEEE002" in result.output
        assert "IEEE003" in result.output


def test_fix_dry_run_does_not_write_file() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        tex = Path("main.tex")
        original = _problematic_tex()
        tex.write_text(original, encoding="utf-8")

        result = runner.invoke(main, ["fix", "main.tex", "--template", "ieee", "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run only" in result.output
        assert tex.read_text(encoding="utf-8") == original


def test_fix_applies_changes_and_backup() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        tex = Path("main.tex")
        tex.write_text(_problematic_tex(), encoding="utf-8")

        result = runner.invoke(main, ["fix", "main.tex", "--template", "ieee"])
        assert result.exit_code == 0
        assert Path("main.tex.bak").exists()

        updated = tex.read_text(encoding="utf-8")
        assert "\\citep{" not in updated
        assert "\\cite{" in updated