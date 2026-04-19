from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

try:
    import tomllib  # type: ignore[attr-defined]
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

from paperfmt.core.models import RuleOverride
from paperfmt.core.registry import DEFAULT_TEMPLATE, normalize_template
from paperfmt.core.rules import get_template_rule_defaults


@dataclass(slots=True)
class ProjectConfig:
    template: str = DEFAULT_TEMPLATE
    main_tex: str = "main.tex"
    bibliography: str = "references.bib"
    state_dir: str = ".paperfmt"
    rules: dict[str, RuleOverride] | None = None


def _default_rule_severities() -> Iterable[tuple[str, str]]:
    return get_template_rule_defaults().items()


def default_config_text(template: str = DEFAULT_TEMPLATE) -> str:
    lines = [
        "[paperfmt]",
        f'template = "{normalize_template(template)}"',
        'main_tex = "main.tex"',
        'bibliography = "references.bib"',
        'state_dir = ".paperfmt"',
        "",
    ]

    for rule_id, severity in _default_rule_severities():
        lines.extend(
            [
                f"[rules.{rule_id}]",
                "enabled = true",
                f'severity = "{severity}"',
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def load_project_config(config_path: Path) -> ProjectConfig:
    if not config_path.exists():
        return ProjectConfig(rules={})

    data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    paperfmt = data.get("paperfmt", {})
    rules_raw = data.get("rules", {})

    rules: dict[str, RuleOverride] = {}
    if isinstance(rules_raw, dict):
        for rule_id, raw in rules_raw.items():
            if not isinstance(raw, dict):
                continue
            rules[rule_id] = RuleOverride(
                enabled=bool(raw.get("enabled", True)),
                severity=str(raw["severity"]).lower() if raw.get("severity") is not None else None,
            )

    return ProjectConfig(
        template=normalize_template(str(paperfmt.get("template", DEFAULT_TEMPLATE))),
        main_tex=str(paperfmt.get("main_tex", "main.tex")),
        bibliography=str(paperfmt.get("bibliography", "references.bib")),
        state_dir=str(paperfmt.get("state_dir", ".paperfmt")),
        rules=rules,
    )


def write_default_config(config_path: Path, template: str) -> None:
    config_path.write_text(default_config_text(template=template), encoding="utf-8")
