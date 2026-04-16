from __future__ import annotations

from paperfmt.core.errors import BuildResult


def print_build_summary(result: BuildResult) -> None:
    print(f"BUILD OK: {result.output_pdf} ({result.duration_seconds:.2f}s)")
    if result.kept_tex:
        print(f"- kept tex: {result.kept_tex}")
    if result.kept_log:
        print(f"- kept log: {result.kept_log}")
