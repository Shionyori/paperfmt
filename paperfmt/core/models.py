from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class RuleOverride:
    enabled: bool = True
    severity: str | None = None


@dataclass(slots=True)
class Diagnostic:
    rule_id: str
    severity: str
    message: str
    line: int
    can_fix: bool = False


@dataclass(slots=True)
class CheckReport:
    input_file: Path
    template: str
    diagnostics: list[Diagnostic]

    @property
    def error_count(self) -> int:
        return sum(1 for d in self.diagnostics if d.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for d in self.diagnostics if d.severity == "warning")


@dataclass(slots=True)
class FixReport:
    input_file: Path
    changed: bool
    applied_fixes: list[str]
    original_text: str
    fixed_text: str


@dataclass(slots=True)
class RuleSet:
    template: str
    bibliography: str = "references.bib"
    rules: dict[str, RuleOverride] | None = None

    def is_enabled(self, rule_id: str) -> bool:
        if not self.rules or rule_id not in self.rules:
            return True
        return self.rules[rule_id].enabled

    def resolve_severity(self, rule_id: str, default: str) -> str:
        if not self.rules or rule_id not in self.rules:
            return default
        override = self.rules[rule_id].severity
        if override in {"error", "warning", "info"}:
            return override
        return default
