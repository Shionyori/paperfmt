from __future__ import annotations

from importlib.resources import files
from pathlib import Path


TEMPLATE_REGISTRY: dict[str, dict[str, str]] = {
    "ieee": {
        "main.tex": "templates/ieee/main.tex.tmpl",
        "refs.bib": "templates/ieee/refs.bib",
    }
}


def supported_templates() -> tuple[str, ...]:
    return tuple(TEMPLATE_REGISTRY.keys())


def _read_asset(relative_path: str) -> str:
    asset_path = files("paperfmt") / "assets" / relative_path
    return asset_path.read_text(encoding="utf-8")


def _render_main_tex(template_text: str, title: str, anonymous: bool, authors: tuple[str, ...]) -> str:
    author_line = "Anonymous Author(s)"
    if not anonymous:
        filtered = [a.strip() for a in authors if a.strip()]
        author_line = " \\and ".join(filtered) if filtered else "First Author \\and Second Author"

    rendered = template_text.replace("__TITLE__", title.strip() or "Paper Title")
    rendered = rendered.replace("__AUTHOR_LINE__", author_line)
    return rendered


def create_project_scaffold(
    template: str,
    output_dir: Path,
    force: bool = False,
    title: str = "Paper Title",
    anonymous: bool = True,
    authors: tuple[str, ...] = (),
) -> list[Path]:
    if template not in TEMPLATE_REGISTRY:
        raise ValueError(f"Unsupported template: {template}")

    output_dir.mkdir(parents=True, exist_ok=True)

    template_files = TEMPLATE_REGISTRY[template]
    main_tex = _render_main_tex(
        template_text=_read_asset(template_files["main.tex"]),
        title=title,
        anonymous=anonymous,
        authors=authors,
    )
    refs_bib = _read_asset(template_files["refs.bib"])

    files = {
        output_dir / "main.tex": main_tex,
        output_dir / "refs.bib": refs_bib,
    }

    created: list[Path] = []
    for path, content in files.items():
        if path.exists() and not force:
            raise FileExistsError(f"Refusing to overwrite existing file: {path}")
        path.write_text(content, encoding="utf-8")
        created.append(path)

    return created