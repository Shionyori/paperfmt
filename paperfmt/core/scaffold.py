from __future__ import annotations

import shutil
from pathlib import Path

from paperfmt.core.project_config import write_default_config
from paperfmt.core.registry import is_supported_template, normalize_template, supported_templates as registry_supported_templates


def supported_templates() -> tuple[str, ...]:
    return registry_supported_templates()


def create_project_scaffold(
    template: str,
    output_dir: Path,
    force: bool = False,
) -> list[Path]:
    resolved_template = normalize_template(template)
    if not is_supported_template(resolved_template):
        raise ValueError(f"Unsupported template: {template}")

    output_dir.mkdir(parents=True, exist_ok=True)

    state_dir = output_dir / ".paperfmt"
    backup_dir = state_dir / "backup"
    report_file = state_dir / "report.txt"
    config_file = output_dir / "paperfmt.toml"

    files = {config_file: "", report_file: ""}

    created: list[Path] = []
    backup_dir.mkdir(parents=True, exist_ok=True)

    for path, content in files.items():
        if path.exists() and not force:
            continue

        if path == config_file:
            write_default_config(path, template=resolved_template)
        elif path == report_file:
            path.write_text("[paperfmt] init completed\n", encoding="utf-8")
        else:
            path.write_text(content, encoding="utf-8")
        created.append(path)

    backup_path = backup_dir / "main.tex.bak"
    main_tex_path = output_dir / "main.tex"
    if main_tex_path.exists() and (force or not backup_path.exists()):
        shutil.copy2(main_tex_path, backup_path)
        created.append(backup_path)

    return created