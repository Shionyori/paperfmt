from __future__ import annotations

from dataclasses import dataclass


class PaperfmtError(RuntimeError):
    pass


class DependencyError(PaperfmtError):
    pass


class ConfigError(PaperfmtError):
    pass


class CompileError(PaperfmtError):
    pass


class TemplateError(PaperfmtError):
    pass


@dataclass(slots=True)
class BuildResult:
    output_pdf: str
    duration_seconds: float
    style: str
    kept_tex: str | None = None
    kept_log: str | None = None


def format_error(exc: Exception) -> str:
    if isinstance(exc, DependencyError):
        return f"Dependency error: {exc}"
    if isinstance(exc, ConfigError):
        return f"Config error: {exc}"
    if isinstance(exc, TemplateError):
        return f"Template error: {exc}"
    if isinstance(exc, CompileError):
        return f"Compile error: {exc}"
    return str(exc)
