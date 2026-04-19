from __future__ import annotations

from paperfmt.core.registry import DEFAULT_TEMPLATE, normalize_template
from paperfmt.core.rules.base import RulePlugin
from paperfmt.core.rules.ieee_conf import RULES as IEEE_CONF_RULES


TEMPLATE_RULES: dict[str, tuple[RulePlugin, ...]] = {
    "ieee-conf": IEEE_CONF_RULES,
}


def get_template_plugins(template: str) -> tuple[RulePlugin, ...]:
    normalized = normalize_template(template)
    return TEMPLATE_RULES.get(normalized, ())


def get_template_rule_defaults(template: str = DEFAULT_TEMPLATE) -> dict[str, str]:
    plugins = get_template_plugins(template)
    return {plugin.rule_id: plugin.default_severity for plugin in plugins}
