"""Helpers for converting WAF policy input into OCI SDK models."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    build_model,
    normalize_enum_values,
    serialize_oci_model,
)


def build_response_body(models, value):
    """Build a static HTTP response body model from module input.

    Args:
        models: OCI WAF model namespace.
        value: Static body input.

    Returns:
        A static response body model, or None.
    """
    if value is None:
        return None
    return build_model(
        normalize_enum_values(value, {"type"}),
        models.StaticTextHttpResponseBody,
    )


def build_action(models, value):
    """Build an action model, including static response headers and body.

    Args:
        models: OCI WAF model namespace.
        value: Action input.

    Returns:
        A typed OCI action model.
    """
    action_type = normalize_enum_values(value, {"type"})["type"]
    model_name = {
        "ALLOW": "AllowAction",
        "CHECK": "CheckAction",
        "RETURN_HTTP_RESPONSE": "ReturnHttpResponseAction",
    }[action_type]
    if action_type != "RETURN_HTTP_RESPONSE":
        return build_model(
            {"type": action_type, "name": value.get("name")},
            getattr(models, model_name),
        )
    headers = value.get("headers")
    if headers is not None:
        headers = [build_model(item, models.ResponseHeader) for item in headers]
    return build_model(
        {
            "type": action_type,
            "name": value.get("name"),
            "code": value.get("code"),
            "headers": headers,
            "body": build_response_body(models, value.get("body")),
        },
        getattr(models, model_name),
    )


def build_protection_capability(models, value):
    """Build a protection capability and its nested exclusion models.

    Args:
        models: OCI WAF model namespace.
        value: Capability input.

    Returns:
        A typed protection capability model.
    """
    exclusions = value.get("exclusions")
    if exclusions is not None:
        exclusions = build_model(exclusions, models.ProtectionCapabilityExclusions)
    weights = value.get("collaborative_weights")
    if weights is not None:
        weights = [
            build_model(item, models.CollaborativeCapabilityWeightOverride)
            for item in weights
        ]
    return build_model(
        dict(value, exclusions=exclusions, collaborative_weights=weights),
        models.ProtectionCapability,
    )


def _build_rate_limiting_rule(models, rule):
    """Build a rate-limiting rule from normalized input."""
    rule["type"] = "REQUEST_RATE_LIMITING"
    if rule.get("configurations") is not None:
        rule["configurations"] = [
            build_model(item, models.RequestRateLimitingConfiguration)
            for item in rule["configurations"]
        ]
    return build_model(rule, models.RequestRateLimitingRule)


def _build_protection_rule(models, rule):
    """Build a protection rule from normalized input."""
    rule["type"] = "PROTECTION"
    if rule.get("protection_capabilities") is not None:
        rule["protection_capabilities"] = [
            build_protection_capability(models, item)
            for item in rule["protection_capabilities"]
        ]
    settings = rule.get("protection_capability_settings")
    if settings is not None:
        rule["protection_capability_settings"] = build_model(
            settings, models.ProtectionCapabilitySettings
        )
    return build_model(rule, models.ProtectionRule)


def build_rule(models, value, rule_kind):
    """Normalize rule input and select the builder for its policy section.

    Args:
        models: OCI WAF model namespace.
        value: Rule input.
        rule_kind: Section name that identifies the rule model.

    Returns:
        A typed OCI rule model.
    """
    rule = normalize_enum_values(value, {"condition_language"})
    if rule_kind.endswith("rate_limiting"):
        return _build_rate_limiting_rule(models, rule)
    if rule_kind.endswith("protection"):
        return _build_protection_rule(models, rule)
    rule["type"] = "ACCESS_CONTROL"
    return build_model(rule, models.AccessControlRule)


def build_section(models, value, section_kind):
    """Build one WAF policy request or response section.

    Args:
        models: OCI WAF model namespace.
        value: Section input.
        section_kind: Section name used to select the SDK model.

    Returns:
        A typed policy section model, or None.

    Raises:
        ValueError: If the section name is unsupported.
    """
    if value is None:
        return None
    section = dict(value)
    if section.get("rules") is not None:
        section["rules"] = [
            build_rule(models, item, section_kind) for item in section["rules"]
        ]
    model_name = {
        "request_rate_limiting": "RequestRateLimiting",
        "request_protection": "RequestProtection",
        "response_protection": "ResponseProtection",
        "request_access_control": "RequestAccessControl",
        "response_access_control": "ResponseAccessControl",
    }.get(section_kind)
    if model_name is None:
        raise ValueError("Unsupported WAF section kind: %s" % section_kind)
    return build_model(section, getattr(models, model_name))


def build_policy_fields(models, params):
    """Build typed policy fields shared by create and update requests.

    Args:
        models: OCI WAF model namespace.
        params: Module parameter dictionary.

    Returns:
        A dictionary of typed policy fields.
    """
    fields = {
        "display_name": params.get("name"),
        "actions": None,
        "request_access_control": build_section(
            models, params.get("request_access_control"), "request_access_control"
        ),
        "request_rate_limiting": build_section(
            models, params.get("request_rate_limiting"), "request_rate_limiting"
        ),
        "request_protection": build_section(
            models, params.get("request_protection"), "request_protection"
        ),
        "response_access_control": build_section(
            models, params.get("response_access_control"), "response_access_control"
        ),
        "response_protection": build_section(
            models, params.get("response_protection"), "response_protection"
        ),
        "freeform_tags": params.get("freeform_tags"),
        "defined_tags": params.get("defined_tags"),
        "system_tags": params.get("system_tags"),
    }
    if params.get("actions") is not None:
        fields["actions"] = [build_action(models, item) for item in params["actions"]]
    return {key: value for key, value in fields.items() if value is not None}


def normalize_waf(value, field_name=None):
    """Return policy input in plain Python form for comparison.

    Args:
        value: SDK model or module value.
        field_name: Current schema field name.

    Returns:
        A recursively normalized value.
    """
    if isinstance(value, list):
        return [normalize_waf(item, field_name) for item in value]
    if isinstance(value, dict):
        return {key: normalize_waf(item, key) for key, item in value.items()}
    if hasattr(value, "swagger_types") or hasattr(value, "__dict__"):
        return normalize_waf(serialize_oci_model(value), field_name)
    if field_name in ("type", "condition_language") and isinstance(value, str):
        return value.lower()
    return value


def waf_subset_differs(current, desired, _field_name=None):
    """Compare desired nested policy fields while preserving server defaults.

    Args:
        current: Current SDK value.
        desired: Desired module value.
        _field_name: Internal schema field name for enum conversion.

    Returns:
        True when the desired value differs.
    """
    current = normalize_waf(current, _field_name)
    desired = normalize_waf(desired, _field_name)
    if isinstance(desired, dict):
        if current is None:
            current = {}
        if not isinstance(current, dict):
            return True
        return any(
            value is not None and waf_subset_differs(current.get(key), value, key)
            for key, value in desired.items()
        )
    if isinstance(desired, list):
        return _waf_lists_differ(current, desired, _field_name)
    return current != desired


def _waf_lists_differ(current, desired, field_name):
    """Compare actions by name and other lists by position."""
    if current is None:
        current = []
    if not isinstance(current, list):
        return True
    if (
        field_name == "actions"
        and desired
        and all(isinstance(item, dict) and "name" in item for item in desired)
    ):
        current_by_name = {
            item.get("name"): item for item in current if isinstance(item, dict)
        }
        desired_names = {item["name"] for item in desired}
        return (
            len(current) != len(desired)
            or set(current_by_name) != desired_names
            or any(
                waf_subset_differs(current_by_name[item["name"]], item, field_name)
                for item in desired
            )
        )
    return len(current) != len(desired) or any(
        waf_subset_differs(current_item, desired_item, field_name)
        for current_item, desired_item in zip(current, desired)
    )
