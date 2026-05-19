from pathlib import Path

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


def test_fix_interactive_no_fixable_diagnostics() -> None:
    """Compliant file produces 'No fixable diagnostics found.'"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "ieee-conf"])
        Path("main.tex").write_text(
            "\\documentclass{IEEEtran}\n"
            "\\title{Test}\n"
            "\\author{Author}\n"
            "\\begin{document}\n"
            "\\maketitle\n"
            "\\begin{abstract}\n"
            "Abstract text.\n"
            "\\end{abstract}\n"
            "\\begin{IEEEkeywords}\n"
            "keyword.\n"
            "\\end{IEEEkeywords}\n"
            "\\section{Intro}\n"
            "Text with \\cite{ref1}.\n"
            "\\begin{figure}\n"
            "\\includegraphics{fig.png}\n"
            "\\caption{Figure}\n"
            "\\label{fig:1}\n"
            "\\end{figure}\n"
            "\\ref{fig:1} referenced.\n"
            "\\bibliographystyle{IEEEtran}\n"
            "\\bibliography{refs}\n"
            "\\balance\n"
            "\\end{document}\n",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["fix", "--interactive"])
        # Should find no fixable diagnostics on compliant input
        # (may have non-fixable warnings from PAGE-LIMIT, etc.)
        assert "No fixable diagnostics found." in result.output


def test_fix_interactive_yes_applies_fix() -> None:
    """Pressing 'y' applies the fix and modifies the file."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "ieee-conf"])
        tex = Path("main.tex")
        tex.write_text(
            "\\documentclass{IEEEtran}\n"
            "\\title{Test}\n"
            "\\author{Someone}\n"
            "\\begin{document}\n"
            "\\maketitle\n"
            "\\begin{abstract}\n"
            "Abstract.\n"
            "\\end{abstract}\n"
            "\\begin{IEEEkeywords}\nkeyword.\n\\end{IEEEkeywords}\n"
            "\\bibliography{refs}\n"
            "\\balance\n"
            "\\end{document}\n",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["fix", "--interactive", "--no-backup"], input="y\n")
        assert result.exit_code == 0
        updated = tex.read_text(encoding="utf-8")
        assert "\\bibliographystyle{IEEEtran}" in updated


def test_fix_interactive_no_skips() -> None:
    """Pressing 'n' skips the fix; file remains unchanged."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "ieee-conf"])
        tex = Path("main.tex")
        original = (
            "\\documentclass{IEEEtran}\n"
            "\\title{Test}\n"
            "\\author{Someone}\n"
            "\\begin{document}\n"
            "\\maketitle\n"
            "\\begin{abstract}\n"
            "Abstract.\n"
            "\\end{abstract}\n"
            "\\begin{IEEEkeywords}\nkeyword.\n\\end{IEEEkeywords}\n"
            "\\bibliography{refs}\n"
            "\\balance\n"
            "\\end{document}\n"
        )
        tex.write_text(original, encoding="utf-8")
        result = runner.invoke(main, ["fix", "--interactive", "--no-backup"], input="n\n")
        assert result.exit_code == 0
        assert tex.read_text(encoding="utf-8") == original
        assert "No fixes applied" in result.output


def test_fix_interactive_skip_rule_drops_same_rule() -> None:
    """Pressing 's' skips all diagnostics with the current rule_id."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "neurips"])
        tex = Path("main.tex")
        tex.write_text(
            "\\documentclass{neurips_2024}\n"
            "\\usepackage[preprint]{neurips_2024}\n"
            "\\title{Test}\n"
            "\\begin{document}\n"
            "\\maketitle\n"
            "\\begin{abstract}\n"
            "Abstract.\n"
            "\\end{abstract}\n"
            "\\section{Introduction}\n"
            "See \\cite{a} and \\cite{b} for details.\n"
            "\\bibliographystyle{plain}\n"
            "\\bibliography{refs}\n"
            "\\end{document}\n",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["fix", "--interactive", "--no-backup"], input="s\n")
        assert result.exit_code == 0
        assert "Skipped all" in result.output
        # NEUR006 diagnostics should all be skipped
        assert "No fixes applied" in result.output


def test_fix_interactive_all_applies_remaining() -> None:
    """Pressing 'a' applies all remaining fixes silently."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "ieee-conf"])
        tex = Path("main.tex")
        tex.write_text(
            "\\documentclass{IEEEtran}\n"
            "\\title{Test}\n"
            "\\author{Someone}\n"
            "\\begin{document}\n"
            "\\maketitle\n"
            "\\begin{abstract}\n"
            "Abstract.\n"
            "\\end{abstract}\n"
            "\\begin{IEEEkeywords}\nkeyword.\n\\end{IEEEkeywords}\n"
            "\\bibliography{refs}\n"
            "\\balance\n"
            "\\end{document}\n",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["fix", "--interactive", "--no-backup"], input="a\n")
        assert result.exit_code == 0
        updated = tex.read_text(encoding="utf-8")
        # "a" applies all fixes — missing bibliographystyle should be added
        assert "\\bibliographystyle{IEEEtran}" in updated


def test_fix_interactive_quit_preserves_applied() -> None:
    """Pressing 'y' then 'q' writes the first fix and exits."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["init", "--template", "ieee-conf"])
        tex = Path("main.tex")
        tex.write_text(
            "\\documentclass{IEEEtran}\n"
            "\\title{Test}\n"
            "\\author{Someone}\n"
            "\\begin{document}\n"
            "\\maketitle\n"
            "\\begin{abstract}\n"
            "Abstract.\n"
            "\\end{abstract}\n"
            "\\begin{IEEEkeywords}\nkeyword.\n\\end{IEEEkeywords}\n"
            "Text \\cite{ref1 ref2}.\n"
            "\\bibliography{refs}\n"
            "\\balance\n"
            "\\end{document}\n",
            encoding="utf-8",
        )
        result = runner.invoke(main, ["fix", "--interactive", "--no-backup"], input="y\nq\n")
        assert result.exit_code == 0
        assert "Quit after" in result.output
        updated = tex.read_text(encoding="utf-8")
        # First fix (IEEE009 for space-separated cite keys) should be applied before quit
        assert "Applied" in result.output
        assert "\\cite{ref1, ref2}" in updated


def test_fix_interactive_help_shows_flag() -> None:
    """fix --help shows the --interactive flag."""
    runner = CliRunner()
    result = runner.invoke(main, ["fix", "--help"])
    assert result.exit_code == 0
    assert "--interactive" in result.output
    assert "Step through fixes" in result.output
