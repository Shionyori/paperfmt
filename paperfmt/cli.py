from __future__ import annotations

from pathlib import Path

import click

from paperfmt import __version__
from paperfmt.core.artifacts import print_build_summary
from paperfmt.core.compiler import compile_markdown
from paperfmt.core.config import load_effective_config
from paperfmt.core.errors import PaperfmtError, format_error
from paperfmt.core.normalize import normalize_markdown_text, parse_front_matter
from paperfmt.core.templates import resolve_template_path


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """paperfmt: a CLI-first document compiler for academic paper formatting."""


@main.command("build")
@click.argument("input_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--style", default=None, help="Template style. MVP supports: ieee")
@click.option("-o", "--output", default=None, type=click.Path(dir_okay=False, path_type=Path), help="Output PDF path")
@click.option("--config", "config_path", default=None, type=click.Path(exists=True, dir_okay=False, path_type=Path), help="Path to paperfmt.yaml")
@click.option("--keep-tex", is_flag=True, default=False, help="Keep intermediate .tex file")
@click.option("--keep-log", is_flag=True, default=False, help="Keep compiler log file")
@click.option("--timeout", "timeout_seconds", default=None, type=int, help="Compile timeout in seconds")
@click.option("-v", "verbose", count=True, help="Verbose logging, use -vv for command details")
def build(
    input_file: Path,
    style: str | None,
    output: Path | None,
    config_path: Path | None,
    keep_tex: bool,
    keep_log: bool,
    timeout_seconds: int | None,
    verbose: int,
) -> None:
    """Compile Markdown into a submission-ready PDF using fixed templates."""
    try:
        project_root = input_file.resolve().parent
        config = load_effective_config(
            project_root=project_root,
            explicit_config_path=config_path,
            cli_overrides={
                "style": style,
                "keep_tex": keep_tex if keep_tex else None,
                "keep_log": keep_log if keep_log else None,
                "timeout_seconds": timeout_seconds,
            },
        )

        if config.style != "ieee":
            raise PaperfmtError("MVP currently supports only --style ieee")

        output_pdf = output or (project_root / config.output_dir / f"{input_file.stem}.pdf")

        raw_text = input_file.read_text(encoding="utf-8")
        metadata, body = parse_front_matter(raw_text)
        normalized_text = normalize_markdown_text(body=body, metadata=metadata, project_root=project_root)

        template_path = resolve_template_path(config.style)

        result = compile_markdown(
            input_file=input_file,
            normalized_markdown=normalized_text,
            style=config.style,
            template_path=template_path,
            output_pdf=output_pdf,
            engine=config.engine,
            timeout_seconds=config.timeout_seconds,
            keep_tex=config.keep_tex,
            keep_log=config.keep_log,
            verbose=verbose,
        )

        print_build_summary(result)

    except PaperfmtError as exc:
        raise click.ClickException(format_error(exc))
