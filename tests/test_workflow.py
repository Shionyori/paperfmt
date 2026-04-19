from __future__ import annotations

import json
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


def test_init_named_authors_and_title() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            main,
            [
                "init",
                "--template",
                "ieee",
                "--named",
                "--title",
                "My Paper",
                "--author",
                "Alice",
                "--author",
                "Bob",
            ],
        )
        assert result.exit_code == 0
        main_tex = Path("main.tex").read_text(encoding="utf-8")
        assert "\\title{My Paper}" in main_tex
        assert "\\\\title{My Paper}" not in main_tex
        assert "\\author{Alice \\and Bob}" in main_tex


def test_check_reports_findings() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("main.tex").write_text(_problematic_tex(), encoding="utf-8")

        result = runner.invoke(main, ["check", "main.tex", "--template", "ieee"])
        assert result.exit_code == 0
        assert "IEEE001" in result.output
        assert "IEEE002" in result.output
        assert "IEEE003" in result.output


def test_check_json_includes_schema_and_template() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("main.tex").write_text(_problematic_tex(), encoding="utf-8")

        result = runner.invoke(main, ["check", "main.tex", "--template", "ieee", "--format", "json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["schema_version"] == "1.0"
        assert payload["template"] == "ieee"


def test_check_reports_anonymization_and_missing_doi() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        tex = Path("main.tex")
        bib = Path("refs.bib")

        tex.write_text(
            """\\documentclass[conference]{IEEEtran}
\\title{Demo}
\\author{John Doe}
\\begin{document}
\\maketitle
\\begin{abstract}
Demo abstract.
\\end{abstract}
\\begin{IEEEkeywords}
paperfmt
\\end{IEEEkeywords}
See \\cite{a1}.
\\bibliography{refs}
\\end{document}
""",
            encoding="utf-8",
        )
        bib.write_text(
            """@article{a1,
  author = {John Doe},
  title = {No DOI Entry},
  journal = {Demo Journal},
  year = {2024}
}
""",
            encoding="utf-8",
        )

        result = runner.invoke(main, ["check", "main.tex", "--template", "ieee"])
        assert result.exit_code == 0
        assert "IEEE006" in result.output
        assert "IEEE007" in result.output


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