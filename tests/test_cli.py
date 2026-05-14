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
