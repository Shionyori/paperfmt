from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from paperfmt.core.errors import ConfigError


@dataclass(slots=True)
class EffectiveConfig:
    style: str = "ieee"
    engine: str = "xelatex"
    timeout_seconds: int = 30
    output_dir: str = "dist"
    keep_tex: bool = False
    keep_log: bool = False


DEFAULTS_PATH = Path(__file__).resolve().parents[1] / "defaults" / "ieee.yaml"


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"Cannot read config file: {path}") from exc

    data = yaml.safe_load(text) or {}
    if not isinstance(data, dict):
        raise ConfigError(f"Config must be a YAML mapping: {path}")
    return data


def load_effective_config(
    project_root: Path,
    explicit_config_path: Path | None,
    cli_overrides: dict[str, Any],
) -> EffectiveConfig:
    merged: dict[str, Any] = {}

    if DEFAULTS_PATH.exists():
        merged.update(_read_yaml(DEFAULTS_PATH))

    global_path = Path.home() / ".config" / "paperfmt" / "defaults.yaml"
    if global_path.exists():
        merged.update(_read_yaml(global_path))

    project_path = explicit_config_path or (project_root / "paperfmt.yaml")
    if project_path.exists():
        merged.update(_read_yaml(project_path))

    for key, value in cli_overrides.items():
        if value is not None:
            merged[key] = value

    try:
        cfg = EffectiveConfig(
            style=str(merged.get("style", "ieee")),
            engine=str(merged.get("engine", "xelatex")),
            timeout_seconds=int(merged.get("timeout_seconds", 30)),
            output_dir=str(merged.get("output_dir", "dist")),
            keep_tex=bool(merged.get("keep_tex", False)),
            keep_log=bool(merged.get("keep_log", False)),
        )
    except (TypeError, ValueError) as exc:
        raise ConfigError("Invalid config value type") from exc

    if cfg.timeout_seconds <= 0:
        raise ConfigError("timeout_seconds must be > 0")

    return cfg
