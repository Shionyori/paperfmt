from __future__ import annotations

DEFAULT_TEMPLATE = "ieee-conf"

TEMPLATE_ALIASES: dict[str, str] = {}

CANONICAL_TEMPLATES: tuple[str, ...] = (DEFAULT_TEMPLATE,)


def normalize_template(template: str) -> str:
    return TEMPLATE_ALIASES.get(template, template)


def supported_templates() -> tuple[str, ...]:
    return CANONICAL_TEMPLATES + tuple(TEMPLATE_ALIASES.keys())


def is_supported_template(template: str) -> bool:
    return normalize_template(template) in CANONICAL_TEMPLATES
