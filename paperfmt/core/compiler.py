from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from paperfmt.core.errors import BuildResult, CompileError, DependencyError


def _require_dependency(binary: str, install_hint: str) -> None:
    if shutil.which(binary):
        return
    raise DependencyError(f"Missing '{binary}'. Install hint: {install_hint}")


def _format_compile_error(stderr: str, log_path: str | None) -> str:
    lines = stderr.strip().splitlines() if stderr else []
    excerpt = "\n".join(lines[-12:]) if lines else "No stderr output"

    hint = ""
    if "IEEEtran.cls" in stderr:
        hint = (
            "\nHint: IEEE template requires IEEEtran.cls. "
            "Install TeX package 'texlive-publishers' (Ubuntu/Debian) or the equivalent package on your system."
        )

    log_hint = f"\nBuild log: {log_path}" if log_path else ""
    return f"Pandoc/LaTeX failed. Last log lines:\n{excerpt}{hint}{log_hint}"


def compile_markdown(
    input_file: Path,
    normalized_markdown: str,
    style: str,
    template_path: Path,
    output_pdf: Path,
    engine: str,
    timeout_seconds: int,
    keep_tex: bool,
    keep_log: bool,
    verbose: int,
) -> BuildResult:
    _require_dependency("pandoc", "https://pandoc.org/installing.html")
    _require_dependency("xelatex", "Install TeX Live or MacTeX and ensure xelatex is on PATH")

    start = time.perf_counter()
    output_pdf = output_pdf.resolve()
    output_pdf.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="paperfmt-") as tmp:
        tmpdir = Path(tmp)
        tmp_md = tmpdir / f"{input_file.stem}.normalized.md"
        tmp_pdf = tmpdir / f"{input_file.stem}.pdf"
        tmp_log = tmpdir / "pandoc.log"

        tmp_md.write_text(normalized_markdown, encoding="utf-8")

        cmd = [
            "pandoc",
            str(tmp_md),
            "--standalone",
            f"--template={template_path}",
            f"--pdf-engine={engine}",
            "--pdf-engine-opt=-interaction=nonstopmode",
            "--pdf-engine-opt=-halt-on-error",
            f"--resource-path={input_file.parent.resolve()}",
            "-o",
            str(tmp_pdf),
        ]

        if verbose >= 2:
            print("[paperfmt] Running:", " ".join(cmd))

        try:
            proc = subprocess.run(
                cmd,
                cwd=input_file.parent,
                timeout=timeout_seconds,
                capture_output=True,
                text=True,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise CompileError(f"Compilation timed out after {timeout_seconds}s") from exc

        tmp_log.write_text(
            "STDOUT:\n"
            + (proc.stdout or "")
            + "\n\nSTDERR:\n"
            + (proc.stderr or ""),
            encoding="utf-8",
        )

        if proc.returncode != 0:
            kept_log_path = None
            if keep_log:
                dest_log = output_pdf.with_suffix(".build.log")
                shutil.copy2(tmp_log, dest_log)
                kept_log_path = str(dest_log)
            raise CompileError(_format_compile_error(proc.stderr or "", kept_log_path))

        if not tmp_pdf.exists():
            raise CompileError("Compilation finished without producing PDF")

        shutil.copy2(tmp_pdf, output_pdf)

        kept_tex_path = None
        kept_log_path = None

        if keep_tex:
            tex_cmd = [
                "pandoc",
                str(tmp_md),
                "--standalone",
                f"--template={template_path}",
                "-t",
                "latex",
                "-o",
                str(tmpdir / f"{input_file.stem}.tex"),
            ]
            tex_proc = subprocess.run(tex_cmd, cwd=input_file.parent, capture_output=True, text=True, check=False)
            if tex_proc.returncode == 0:
                dest = output_pdf.with_suffix(".tex")
                shutil.copy2(tmpdir / f"{input_file.stem}.tex", dest)
                kept_tex_path = str(dest)

        if keep_log:
            dest_log = output_pdf.with_suffix(".build.log")
            shutil.copy2(tmp_log, dest_log)
            kept_log_path = str(dest_log)

    duration = time.perf_counter() - start
    return BuildResult(
        output_pdf=str(output_pdf),
        duration_seconds=duration,
        style=style,
        kept_tex=kept_tex_path,
        kept_log=kept_log_path,
    )
