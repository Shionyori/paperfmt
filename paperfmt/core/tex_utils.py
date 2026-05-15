from __future__ import annotations

import re
from pathlib import Path

_INPUT_RE = re.compile(r"\\(?:input|include)\s*\{([^}]+)\}")


def resolve_includes(tex_file: Path, visited: set[Path] | None = None) -> str:
    """Recursively resolve \\input and \\include directives, returning combined text."""
    if visited is None:
        visited = set()

    tex_file = tex_file.resolve()
    if tex_file in visited:
        return f"% [paperfmt] circular include skipped: {tex_file}\n"
    visited.add(tex_file)

    base_dir = tex_file.parent
    text = tex_file.read_text(encoding="utf-8")

    def _replace(match: re.Match[str]) -> str:
        sub_name = match.group(1).strip()
        sub_path = base_dir / sub_name
        if not sub_path.suffix:
            sub_path = sub_path.with_suffix(".tex")
        if not sub_path.exists():
            return match.group(0)
        resolved = resolve_includes(sub_path, visited)
        return f"% [paperfmt] begin include: {sub_path.name}\n{resolved}% [paperfmt] end include\n"

    return _INPUT_RE.sub(_replace, text)
