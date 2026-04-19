from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import tomllib  # type: ignore[attr-defined]
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]


@dataclass(slots=True)
class RuleOverride:
    enabled: bool = True
    severity: str | None = None


@dataclass(slots=True)
class ProjectConfig:
    template: str = "ieee-conf"
    main_tex: str = "main.tex"
    bibliography: str = "references.bib"
    state_dir: str = ".paperfmt"
    rules: dict[str, RuleOverride] | None = None


def default_config_text(template: str = "ieee-conf") -> str:
    return f"""[paperfmt]
template = "{template}"
main_tex = "main.tex"
bibliography = "references.bib"
state_dir = ".paperfmt"

[rules.IEEE001]
enabled = true
severity = "warning"

[rules.IEEE002]
enabled = true
severity = "warning"

[rules.IEEE003]
enabled = true
severity = "warning"

[rules.IEEE004]
enabled = true
severity = "error"

[rules.IEEE005]
enabled = true
severity = "warning"

[rules.IEEE006]
enabled = true
severity = "warning"

[rules.IEEE007]
enabled = true
severity = "warning"
"""


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
        template=str(paperfmt.get("template", "ieee-conf")),
        main_tex=str(paperfmt.get("main_tex", "main.tex")),
        bibliography=str(paperfmt.get("bibliography", "references.bib")),
        state_dir=str(paperfmt.get("state_dir", ".paperfmt")),
        rules=rules,
    )


def write_default_config(config_path: Path, template: str) -> None:
    config_path.write_text(default_config_text(template=template), encoding="utf-8")
