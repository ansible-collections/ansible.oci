from __future__ import absolute_import, division, print_function

__metaclass__ = type

import copy

import oci
import pytest

from .conftest import load_collection_module


@pytest.mark.parametrize(
    "section, model_name, rule_type",
    (
        ("request_access_control", "AccessControlRule", "ACCESS_CONTROL"),
        ("response_access_control", "AccessControlRule", "ACCESS_CONTROL"),
        ("request_rate_limiting", "RequestRateLimitingRule", "REQUEST_RATE_LIMITING"),
        ("request_protection", "ProtectionRule", "PROTECTION"),
        ("response_protection", "ProtectionRule", "PROTECTION"),
    ),
)
@pytest.mark.parametrize("include_nested_fields", (False, True))
def test_rule_type_follows_section(
    section, model_name, rule_type, include_nested_fields
):
    """Infer rule types from sections without changing input or comparison results."""
    helper = load_collection_module("oci_waf")
    rule = {"name": "Rule", "action_name": "Check", "condition_language": "jmespath"}
    if include_nested_fields:
        if section == "request_rate_limiting":
            rule["configurations"] = [{"period_in_seconds": 60, "requests_limit": 100}]
        elif section.endswith("protection"):
            rule["protection_capabilities"] = [{"key": "Capability", "version": 1}]
    original = copy.deepcopy(rule)
    model = helper.build_rule(oci.waf.models, rule, section)

    assert isinstance(model, getattr(oci.waf.models, model_name))
    assert model.type == rule_type
    assert model.condition_language == "JMESPATH"
    assert oci.util.to_dict(model)["type"] == rule_type
    assert not helper.waf_subset_differs(model, rule)
    assert rule == original
    if "configurations" in rule:
        assert isinstance(
            model.configurations[0], oci.waf.models.RequestRateLimitingConfiguration
        )
    if "protection_capabilities" in rule:
        assert isinstance(
            model.protection_capabilities[0], oci.waf.models.ProtectionCapability
        )


def test_typed_models_serialize_nested_policy_fields():
    """Serialize nested policy fields with the SDK minimum version."""
    helper = load_collection_module("oci_waf")
    params = {
        "name": "MixedCase",
        "actions": [
            {"name": "ALLOW", "type": "allow"},
            {"name": "Check", "type": "check"},
            {
                "name": "Deny",
                "type": "return_http_response",
                "code": 403,
                "headers": [{"name": "X-Policy", "value": "UPPERCASE"}],
                "body": {"type": "static_text", "text": "KEEP CASE"},
            },
        ],
        "request_access_control": {
            "default_action_name": "ALLOW",
            "rules": [
                {
                    "name": "ACCESS",
                    "action_name": "Deny",
                    "condition_language": "jmespath",
                    "condition": "KEEP_CASE",
                }
            ],
        },
        "response_access_control": {"rules": []},
        "request_rate_limiting": {
            "rules": [
                {
                    "name": "RATE",
                    "action_name": "Deny",
                    "condition_language": "jmespath",
                    "configurations": [
                        {"period_in_seconds": 60, "requests_limit": 100}
                    ],
                }
            ],
        },
        "request_protection": {
            "body_inspection_size_limit_in_bytes": 8192,
            "rules": [
                {
                    "name": "PROTECT",
                    "action_name": "Check",
                    "is_body_inspection_enabled": True,
                    "protection_capabilities": [
                        {
                            "key": "Capability",
                            "version": 1,
                            "exclusions": {"args": ["ARG"]},
                            "collaborative_weights": [{"key": "Weight", "weight": 2}],
                        }
                    ],
                    "protection_capability_settings": {
                        "allowed_http_methods": ["GET", "POST"],
                        "max_number_of_arguments": 100,
                    },
                }
            ],
        },
        "response_protection": {"rules": []},
        "freeform_tags": {"type": "UPPERCASE"},
        "defined_tags": {"Namespace": {"condition_language": "UNCHANGED"}},
    }
    original = copy.deepcopy(params)
    fields = helper.build_policy_fields(oci.waf.models, params)
    details = oci.waf.models.CreateWebAppFirewallPolicyDetails(
        compartment_id="compartment", **fields
    )
    serializer = object.__new__(oci.base_client.BaseClient)
    serializer.complex_type_mappings = {
        name: getattr(oci.waf.models, name)
        for name in dir(oci.waf.models)
        if isinstance(getattr(oci.waf.models, name), type)
    }
    wire = serializer.sanitize_for_serialization(details)
    assert wire["displayName"] == "MixedCase"
    assert wire["actions"][0] == {"type": "ALLOW", "name": "ALLOW"}
    assert wire["actions"][2]["body"] == {"type": "STATIC_TEXT", "text": "KEEP CASE"}
    assert wire["actions"][2]["headers"][0]["value"] == "UPPERCASE"
    access_rule = wire["requestAccessControl"]["rules"][0]
    assert access_rule["conditionLanguage"] == "JMESPATH"
    assert access_rule["condition"] == "KEEP_CASE"
    assert (
        wire["requestRateLimiting"]["rules"][0]["configurations"][0]["requestsLimit"]
        == 100
    )
    protection = wire["requestProtection"]["rules"][0]
    assert protection["protectionCapabilities"][0]["collaborativeWeights"] == [
        {"key": "Weight", "weight": 2}
    ]
    assert protection["protectionCapabilitySettings"]["allowedHttpMethods"] == [
        "GET",
        "POST",
    ]
    assert wire["freeformTags"] == params["freeform_tags"]
    assert wire["definedTags"] == params["defined_tags"]
    assert params == original


@pytest.mark.parametrize("field", ("name", "condition", "text", "action_name"))
def test_comparison_preserves_case_sensitive_values(field):
    """Detect letter-case changes in user data."""
    helper = load_collection_module("oci_waf")
    assert helper.waf_subset_differs({field: "VALUE"}, {field: "value"})


def test_comparison_ignores_unspecified_defaults_in_ordered_rules():
    """Ignore omitted server defaults while preserving rule order."""
    helper = load_collection_module("oci_waf")
    current = {
        "rules": [
            {
                "type": "ACCESS_CONTROL",
                "name": "One",
                "condition_language": "JMESPATH",
                "condition": "true",
                "action_name": "Allow",
            }
        ]
    }
    desired = {
        "rules": [
            {
                "name": "One",
                "condition_language": None,
                "action_name": "Allow",
            }
        ],
        "default_action_name": None,
    }
    assert not helper.waf_subset_differs(current, desired)
    assert helper.waf_subset_differs(current, {"rules": []})
    assert helper.waf_subset_differs(current, {"rules": desired["rules"] * 2})


def test_actions_compare_by_name_and_rules_compare_by_position():
    """Ignore action order while detecting rule order changes."""
    helper = load_collection_module("oci_waf")
    actions = [{"name": "One", "type": "ALLOW"}, {"name": "Two", "type": "CHECK"}]
    assert not helper.waf_subset_differs(actions, list(reversed(actions)), "actions")
    assert helper.waf_subset_differs(
        {"rules": actions}, {"rules": list(reversed(actions))}
    )


def test_duplicate_action_names_do_not_match_different_actions():
    """Detect action replacement when a desired name appears twice."""
    helper = load_collection_module("oci_waf")
    current = [{"name": "One", "type": "ALLOW"}, {"name": "Two", "type": "ALLOW"}]
    desired = [{"name": "One", "type": "allow"}, {"name": "One", "type": "allow"}]
    assert helper.waf_subset_differs(current, desired, "actions")


def test_empty_sections_match_absent_server_defaults():
    """Keep empty sections unchanged when OCI returns no configured rules."""
    helper = load_collection_module("oci_waf")
    assert not helper.waf_subset_differs(None, {"rules": []})
    assert not helper.waf_subset_differs(None, {"rules": None})
    assert not helper.waf_subset_differs({}, {"rules": []})
    assert helper.waf_subset_differs({"rules": [{"name": "Existing"}]}, {"rules": []})
