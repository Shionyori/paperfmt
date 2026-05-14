from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from paperfmt.core.models import Diagnostic, RuleSet


@dataclass(slots=True)
class RulePlugin:
    rule_id: str
    default_severity: str
    check: Callable[[str, Path, RuleSet], list[Diagnostic]]
    fix: Callable[[str], tuple[str, bool]] | None = None
