from __future__ import annotations

from pathlib import Path

from paperfmt.core.errors import TemplateError


def resolve_template_path(style: str) -> Path:
    if style != "ieee":
        raise TemplateError(f"Unknown template style: {style}")

    path = Path(__file__).resolve().parents[1] / "templates" / "ieee" / "template.tex"
    if not path.exists():
        raise TemplateError(f"Built-in template not found: {path}")
    return path
