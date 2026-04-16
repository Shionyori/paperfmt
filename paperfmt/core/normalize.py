from __future__ import annotations

import re
from pathlib import Path

import yaml

from paperfmt.core.errors import ConfigError


FRONT_MATTER_RE = re.compile(r"^---\n(.*?)\n---\n?", re.DOTALL)
IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")


def parse_front_matter(markdown_text: str) -> tuple[dict, str]:
    match = FRONT_MATTER_RE.match(markdown_text)
    if not match:
        return {}, markdown_text

    yaml_text = match.group(1)
    body = markdown_text[match.end() :]

    try:
        data = yaml.safe_load(yaml_text) or {}
    except yaml.YAMLError as exc:
        raise ConfigError("Invalid YAML front matter") from exc

    if not isinstance(data, dict):
        raise ConfigError("Front matter must be a YAML mapping")

    return data, body


def _normalize_image_path(path_text: str, project_root: Path) -> str:
    stripped = path_text.strip()
    if stripped.startswith(("http://", "https://", "data:")):
        return stripped

    raw_path = stripped.split(" ", 1)[0]
    suffix = stripped[len(raw_path) :]
    absolute_path = (project_root / raw_path).resolve()
    if not absolute_path.exists():
        return stripped

    normalized = absolute_path.as_posix().replace(" ", "\\ ")
    return f"{normalized}{suffix}"


def normalize_markdown_text(body: str, metadata: dict, project_root: Path) -> str:
    def repl(match: re.Match[str]) -> str:
        alt = match.group(1)
        raw_path = match.group(2)
        return f"![{alt}]({_normalize_image_path(raw_path, project_root)})"

    normalized_body = IMAGE_RE.sub(repl, body)

    if metadata:
        front = yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False).strip()
        return f"---\n{front}\n---\n\n{normalized_body.lstrip()}"

    return normalized_body
