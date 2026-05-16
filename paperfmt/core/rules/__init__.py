from __future__ import annotations

from paperfmt.core.registry import DEFAULT_TEMPLATE, normalize_template
from paperfmt.core.rules.base import RulePlugin
from paperfmt.core.rules.ieee_conf import RULES as IEEE_CONF_RULES
from paperfmt.core.rules.acm import RULES as ACM_RULES
# from paperfmt.core.rules.neurips import RULES as NEURIPS_RULES
# from paperfmt.core.rules.acl import RULES as ACL_RULES

TEMPLATE_RULES: dict[str, tuple[RulePlugin, ...]] = {
    "ieee-conf": IEEE_CONF_RULES,
    "acm-conf": ACM_RULES,
    # "neurips": NEURIPS_RULES,
    # "acl-conf": ACL_RULES,
}


def get_template_plugins(template: str) -> tuple[RulePlugin, ...]:
    normalized = normalize_template(template)
    return TEMPLATE_RULES.get(normalized, ())


def get_template_rule_defaults(template: str = DEFAULT_TEMPLATE) -> dict[str, str]:
    plugins = get_template_plugins(template)
    return {plugin.rule_id: plugin.default_severity for plugin in plugins}
