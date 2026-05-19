from __future__ import annotations

from pathlib import Path

from paperfmt.core.models import CheckReport, Diagnostic, FixReport, RuleOverride, RuleSet
from paperfmt.core.registry import is_supported_template, normalize_template
from paperfmt.core.rules import get_template_plugins, get_template_rule_defaults
from paperfmt.core.tex_utils import resolve_includes


def default_ruleset(
    template: str = "ieee-conf", bibliography: str = "references.bib", rules: dict[str, RuleOverride] | None = None
) -> RuleSet:
    return RuleSet(template=normalize_template(template), bibliography=bibliography, rules=rules or {})


def get_rule_defaults(template: str = "ieee-conf") -> dict[str, str]:
    return get_template_rule_defaults(template)


def run_checks(tex_file: Path, template: str, ruleset: RuleSet | None = None) -> CheckReport:
    normalized_template = normalize_template(template)
    if not is_supported_template(normalized_template):
        raise ValueError(f"Unsupported template: {template}")

    active_ruleset = ruleset or default_ruleset(template=normalized_template)
    text = resolve_includes(tex_file)
    diagnostics: list[Diagnostic] = []

    for plugin in get_template_plugins(normalized_template):
        if not active_ruleset.is_enabled(plugin.rule_id):
            continue
        rule_diagnostics = plugin.check(text, tex_file, active_ruleset)
        resolved = active_ruleset.resolve_severity(plugin.rule_id, plugin.default_severity)
        for item in rule_diagnostics:
            diagnostics.append(
                Diagnostic(
                    rule_id=item.rule_id,
                    severity=resolved,
                    message=item.message,
                    line=item.line,
                    can_fix=item.can_fix,
                )
            )

    diagnostics.sort(key=lambda d: (d.line, d.rule_id))
    return CheckReport(input_file=tex_file, template=normalized_template, diagnostics=diagnostics)


def apply_safe_fixes(tex_file: Path, template: str, ruleset: RuleSet | None = None) -> FixReport:
    normalized_template = normalize_template(template)
    if not is_supported_template(normalized_template):
        raise ValueError(f"Unsupported template: {template}")

    active_ruleset = ruleset or default_ruleset(template=normalized_template)
    original_text = tex_file.read_text(encoding="utf-8")
    updated_text = original_text
    applied_fixes: list[str] = []

    for plugin in get_template_plugins(normalized_template):
        if plugin.fix is None:
            continue
        if not active_ruleset.is_enabled(plugin.rule_id):
            continue
        updated_text, changed = plugin.fix(updated_text)
        if changed:
            applied_fixes.append(plugin.rule_id)

    return FixReport(
        input_file=tex_file,
        changed=updated_text != original_text,
        applied_fixes=applied_fixes,
        original_text=original_text,
        fixed_text=updated_text,
    )


def get_fixable_rules(template: str, ruleset: RuleSet) -> dict[str, "RulePlugin"]:
    """Return {rule_id: plugin} for enabled plugins that have a fix function.

    Used by interactive fix mode to look up which plugin to invoke
    when the user approves a diagnostic.
    """
    result: dict[str, "RulePlugin"] = {}
    for plugin in get_template_plugins(template):
        if plugin.fix is not None and ruleset.is_enabled(plugin.rule_id):
            result[plugin.rule_id] = plugin
    return result
