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
        result = runner.invoke(main, ["init", "--template", "ieee-conf"])
        assert result.exit_code == 0
        assert Path("paperfmt.toml").exists()
        assert Path(".paperfmt/report.txt").exists()
        assert Path("main.tex").exists() is False
        assert Path("references.bib").exists() is False


def test_init_keeps_existing_tex_and_creates_backup() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        original = "\\documentclass{article}\n\\begin{document}\nHello\n\\end{document}\n"
        Path("main.tex").write_text(original, encoding="utf-8")

        result = runner.invoke(main, ["init", "--template", "ieee-conf"])
        assert result.exit_code == 0
        assert Path("main.tex").read_text(encoding="utf-8") == original
        assert Path(".paperfmt/backup/main.tex.bak").exists()


def test_check_reports_findings() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "ieee-conf"])
        Path("main.tex").write_text(_problematic_tex(), encoding="utf-8")

        result = runner.invoke(main, ["check"])
        assert result.exit_code == 0
        assert "IEEE001" in result.output
        assert "IEEE002" in result.output
        assert "IEEE003" in result.output


def test_check_json_includes_schema_and_template() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "ieee-conf"])
        Path("main.tex").write_text(_problematic_tex(), encoding="utf-8")

        result = runner.invoke(main, ["check", "--format", "json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["schema_version"] == "1.0"
        assert payload["template"] == "ieee-conf"


def test_check_reports_anonymization_and_missing_doi() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "ieee-conf"])
        tex = Path("main.tex")
        bib = Path("references.bib")

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
\\bibliography{references}
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

        result = runner.invoke(main, ["check"])
        assert result.exit_code == 0
        assert "IEEE006" in result.output
        assert "IEEE007" in result.output


def test_fix_dry_run_does_not_write_file() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "ieee-conf"])
        tex = Path("main.tex")
        original = _problematic_tex()
        tex.write_text(original, encoding="utf-8")

        result = runner.invoke(main, ["fix", "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run only" in result.output
        assert tex.read_text(encoding="utf-8") == original


def test_fix_applies_changes_and_backup() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "ieee-conf"])
        tex = Path("main.tex")
        tex.write_text(_problematic_tex(), encoding="utf-8")

        result = runner.invoke(main, ["fix"])
        assert result.exit_code == 0
        assert Path(".paperfmt/backup/main.tex.bak").exists()

        updated = tex.read_text(encoding="utf-8")
        assert "\\citep{" not in updated
        assert "\\cite{" in updated


def test_ruleset_can_disable_rule() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "ieee-conf"])
        Path("main.tex").write_text(_problematic_tex(), encoding="utf-8")
        Path("paperfmt.toml").write_text(
            Path("paperfmt.toml")
            .read_text(encoding="utf-8")
            .replace(
                "[rules.IEEE003]\nenabled = true",
                "[rules.IEEE003]\nenabled = false",
            ),
            encoding="utf-8",
        )

        result = runner.invoke(main, ["check"])
        assert result.exit_code == 0
        assert "IEEE003" not in result.output


def test_init_adopts_existing_project_without_overwrite() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        original = "\\documentclass{article}\n\\begin{document}\nHello\n\\end{document}\n"
        Path("main.tex").write_text(original, encoding="utf-8")

        result = runner.invoke(main, ["init", "--template", "ieee-conf"])
        assert result.exit_code == 0
        assert Path("paperfmt.toml").exists()
        assert Path(".paperfmt/report.txt").exists()
        assert Path(".paperfmt/backup/main.tex.bak").exists()
        assert Path("main.tex").read_text(encoding="utf-8") == original


def test_init_rejects_removed_template_alias() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["init", "--template", "ieee"])
        assert result.exit_code != 0
        assert "invalid value for '--template'" in result.output.lower()


def test_check_reports_new_format_and_bib_rules() -> None:
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
Demo abstract.
\\end{abstract}
Recent advances [1] show progress.
As shown in Eq. (1), we optimize loss.
\\begin{table}
\\caption{Demo table}
\\begin{tabular}{c}
\\hline
A \\\\
\\hline
\\end{tabular}
\\end{table}
See \\cite{known_ref,missing_ref}.
\\bibliography{references}
\\end{document}
""",
            encoding="utf-8",
        )

        Path("references.bib").write_text(
            """@article{known_ref,
    author = {Alice},
    title = {Known},
    journal = {Demo},
    year = {2024},
    doi = {10.1000/known}
}

@article{unused_ref,
    author = {Bob},
    title = {Unused},
    journal = {Demo},
    year = {2024},
    doi = {10.1000/unused}
}
""",
            encoding="utf-8",
        )

        result = runner.invoke(main, ["check"])
        assert result.exit_code == 0
        assert "CITE-MANUAL" in result.output
        assert "REF-HARDCODE" in result.output
        assert "TAB-FORMAT" in result.output
        assert "BIB-CROSSCHECK" in result.output


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
        assert "\\input{missing}" in result


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
        assert "IEEE001" in result.output
        assert "IEEE003" in result.output


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
