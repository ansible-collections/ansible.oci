from __future__ import absolute_import, division, print_function

import types

import pytest

from .conftest import (
    DummyModule,
    FailJsonCalled,
    make_module_instance,
    load_collection_module,
)


def test_real_sdk_builds_nested_policy_models():
    """Verify real sdk builds nested policy models."""
    import oci

    module_obj = load_collection_module("oci_waf_web_app_firewall_policy")
    details = module_obj.build_create_web_app_firewall_policy_details(
        {
            "compartment_id": "compartment1",
            "name": "policy-name",
            "actions": [
                {
                    "name": "deny",
                    "type": "return_http_response",
                    "code": 403,
                    "body": {"type": "static_text", "text": "Keep Case"},
                }
            ],
            "request_access_control": {
                "default_action_name": "deny",
                "rules": [
                    {
                        "name": "rule-name",
                        "condition_language": "jmespath",
                        "condition": "request.headers['X-Test'] == 'Value'",
                        "action_name": "deny",
                    }
                ],
            },
        }
    )
    assert isinstance(details, oci.waf.models.CreateWebAppFirewallPolicyDetails)
    assert details.actions[0].type == "RETURN_HTTP_RESPONSE"
    assert details.actions[0].body.text == "Keep Case"
    assert details.request_access_control.rules[0].type == "ACCESS_CONTROL"
    assert (
        details.request_access_control.rules[0].condition
        == "request.headers['X-Test'] == 'Value'"
    )


def test_nested_comparison_preserves_case_and_rule_order(monkeypatch):
    """Verify nested comparison preserves case and rule order."""
    module_obj = load_collection_module("oci_waf_web_app_firewall_policy")
    instance = make_module_instance(
        module_obj,
        "OciWafWebAppFirewallPolicyModule",
        {},
        client=types.SimpleNamespace(),
    )
    current = {
        "actions": [{"name": "one", "type": "allow", "description": "server"}],
        "request_access_control": {
            "rules": [
                {"name": "first", "condition": "CaseSensitive"},
                {"name": "second", "condition": "Second"},
            ]
        },
    }
    desired = {
        "actions": [{"name": "one", "type": "ALLOW"}],
        "request_access_control": {
            "rules": [
                {"name": "first", "condition": "CaseSensitive"},
                {"name": "second", "condition": "Second"},
            ]
        },
    }
    assert (
        instance.compare_update_field_values(
            current["actions"], desired["actions"], "waf"
        )
        is False
    )
    assert (
        instance.compare_update_field_values(
            current["request_access_control"], desired["request_access_control"], "waf"
        )
        is False
    )
    reordered = dict(
        desired["request_access_control"],
        rules=list(reversed(desired["request_access_control"]["rules"])),
    )
    assert (
        instance.compare_update_field_values(
            current["request_access_control"], reordered, "waf"
        )
        is True
    )


def test_empty_rule_list_clears_existing_rules():
    """Verify empty rule list clears existing rules."""
    module_obj = load_collection_module("oci_waf_web_app_firewall_policy")
    instance = make_module_instance(
        module_obj,
        "OciWafWebAppFirewallPolicyModule",
        {},
        client=types.SimpleNamespace(),
    )
    assert (
        instance.compare_update_field_values(
            {"rules": [{"name": "one"}]}, {"rules": []}, "waf"
        )
        is True
    )


def test_update_preserves_omitted_fields_in_replaced_section(monkeypatch):
    """Keep existing rules when only the section default action changes."""
    import oci
    from .conftest import FakeResponse

    module = load_collection_module("oci_waf_web_app_firewall_policy")
    current = oci.waf.models.WebAppFirewallPolicy(
        id="policy",
        request_access_control=oci.waf.models.RequestAccessControl(
            default_action_name="Allow",
            rules=[
                oci.waf.models.AccessControlRule(
                    name="Existing",
                    action_name="Allow",
                    condition_language="JMESPATH",
                    condition="true",
                )
            ],
        ),
    )
    calls = []
    client = types.SimpleNamespace(
        update_web_app_firewall_policy=lambda **kwargs: calls.append(kwargs)
        or FakeResponse()
    )
    instance = make_module_instance(
        module,
        "OciWafWebAppFirewallPolicyModule",
        {
            "request_access_control": {"default_action_name": "Deny", "rules": None},
            "wait": False,
        },
        client=client,
    )
    monkeypatch.setattr(
        instance, "call_with_retry", lambda function, **kwargs: function(**kwargs)
    )
    assert instance.update_resource(current) is current
    details = calls[0]["update_web_app_firewall_policy_details"]
    assert details.request_access_control.default_action_name == "Deny"
    assert details.request_access_control.rules[0].name == "Existing"
    assert details.request_access_control.rules[0].condition_language == "JMESPATH"
    assert details.actions is None


def test_nested_arguments_reject_missing_required_values(monkeypatch):
    """Reject incomplete policy actions and rules before any OCI call."""
    from ansible.module_utils.common.arg_spec import ArgumentSpecValidator

    module = load_collection_module("oci_waf_web_app_firewall_policy")
    captured = {}
    monkeypatch.setattr(
        module,
        "AnsibleModule",
        lambda **kwargs: captured.update(kwargs) or DummyModule(),
    )
    monkeypatch.setattr(
        module,
        "OciWafWebAppFirewallPolicyModule",
        lambda instance: types.SimpleNamespace(execute_resource_module=lambda: None),
    )
    module.main()
    validator = ArgumentSpecValidator(captured["argument_spec"])
    for section in (
        "request_access_control",
        "response_access_control",
        "request_rate_limiting",
        "request_protection",
        "response_protection",
    ):
        rule = {"name": "Rule", "action_name": "Check"}
        if section == "request_rate_limiting":
            rule["configurations"] = [{"period_in_seconds": 60, "requests_limit": 100}]
        elif section.endswith("protection"):
            rule["protection_capabilities"] = [{"key": "Capability", "version": 1}]
        value = {"rules": [rule]}
        if section == "request_access_control":
            value["default_action_name"] = "Allow"
        assert not validator.validate({section: value}).error_messages, section
        assert (
            "type"
            not in captured["argument_spec"][section]["options"]["rules"]["options"]
        )
    invalid = (
        {"actions": [{"type": "allow"}]},
        {"actions": [{"name": "Deny", "type": "return_http_response"}]},
        {"request_access_control": {"rules": []}},
        {"response_access_control": {"rules": [{"name": "Rule"}]}},
        {"response_access_control": {"rules": [{"action_name": "Check"}]}},
        {
            "request_access_control": {
                "default_action_name": "Allow",
                "rules": [
                    {"name": "Rule", "type": "protection", "action_name": "Allow"}
                ],
            }
        },
        {
            "request_rate_limiting": {
                "rules": [
                    {
                        "name": "Limit",
                        "action_name": "Deny",
                    }
                ]
            }
        },
        {
            "request_protection": {
                "rules": [
                    {
                        "name": "Protect",
                        "action_name": "Deny",
                        "protection_capabilities": [{"key": "capability"}],
                    }
                ]
            }
        },
    )
    for params in invalid:
        assert validator.validate(params).error_messages, params


@pytest.fixture
def policy_argument_validator(monkeypatch):
    """Return the validator for the policy module argument specification."""
    from ansible.module_utils.common.arg_spec import ArgumentSpecValidator

    module = load_collection_module("oci_waf_web_app_firewall_policy")
    captured = {}
    monkeypatch.setattr(
        module,
        "AnsibleModule",
        lambda **kwargs: captured.update(kwargs) or DummyModule(),
    )
    monkeypatch.setattr(
        module,
        "OciWafWebAppFirewallPolicyModule",
        lambda instance: types.SimpleNamespace(execute_resource_module=lambda: None),
    )
    module.main()
    return ArgumentSpecValidator(captured["argument_spec"])


@pytest.mark.parametrize("section", ("request_protection", "response_protection"))
def test_public_capability_keys_remain_in_results(policy_argument_validator, section):
    """Keep public capability identifiers unchanged after Ansible result filtering."""
    import oci
    from ansible.module_utils.common.parameters import remove_values
    from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
        serialize_oci_model,
    )
    from ansible_collections.ansible.oci.plugins.module_utils.oci_waf import (
        build_policy_fields,
    )

    capability = {
        "key": "942100",
        "version": 1,
        "collaborative_weights": [{"key": "942110", "weight": 2}],
    }
    result = policy_argument_validator.validate(
        {
            section: {
                "rules": [
                    {
                        "name": "Protect",
                        "action_name": "Check",
                        "protection_capabilities": [capability],
                    }
                ]
            }
        }
    )
    assert not result.error_messages
    fields = build_policy_fields(oci.waf.models, result.validated_parameters)
    filtered = remove_values(serialize_oci_model(fields), result._no_log_values)
    returned = filtered[section]["rules"][0]["protection_capabilities"][0]
    assert returned["key"] == "942100"
    assert returned["collaborative_weights"] == [{"key": "942110", "weight": 2}]


@pytest.mark.parametrize("enabled", (True, False))
@pytest.mark.parametrize("section", ("request_protection", "response_protection"))
def test_body_inspection_is_request_only(policy_argument_validator, section, enabled):
    """Accept body inspection only in request protection rules."""
    result = policy_argument_validator.validate(
        {
            section: {
                "rules": [
                    {
                        "name": "Protect",
                        "action_name": "Check",
                        "protection_capabilities": [{"key": "942100", "version": 1}],
                        "is_body_inspection_enabled": enabled,
                    }
                ]
            }
        }
    )
    if section == "request_protection":
        assert not result.error_messages
        assert (
            result.validated_parameters[section]["rules"][0][
                "is_body_inspection_enabled"
            ]
            is enabled
        )
    else:
        assert any(
            "is_body_inspection_enabled" in message
            and "Supported parameters include" in message
            for message in result.error_messages
        )


@pytest.mark.parametrize("action_type", ("allow", "check"))
@pytest.mark.parametrize(
    "field, value",
    (
        ("code", 403),
        ("headers", [{"name": "X-Test", "value": "Value"}]),
        ("headers", []),
        ("body", {"type": "static_text", "text": "Denied"}),
        ("body", {}),
    ),
)
@pytest.mark.parametrize("check_mode", (True, False))
def test_incompatible_action_fields_fail_before_client_creation(
    monkeypatch, action_type, field, value, check_mode
):
    """Reject incompatible action fields before client creation, including check mode."""
    module = load_collection_module("oci_waf_web_app_firewall_policy")
    action = {"name": "Invalid", "type": action_type, field: value}
    dummy = DummyModule(
        {"actions": [{"name": "Valid", "type": "allow"}, action]},
        check_mode=check_mode,
    )
    monkeypatch.setattr(module, "AnsibleModule", lambda **kwargs: dummy)
    monkeypatch.setattr(
        module,
        "OciWafWebAppFirewallPolicyModule",
        lambda instance: pytest.fail("Client construction must not occur"),
    )
    with pytest.raises(FailJsonCalled) as exc:
        module.main()
    message = exc.value.payload["msg"]
    assert "actions[1]" in message
    assert "type=%s" % action_type in message
    assert field in message
    assert "require type=return_http_response" in message


def test_action_error_lists_all_incompatible_fields():
    """List all incompatible fields in one validation error."""
    module = load_collection_module("oci_waf_web_app_firewall_policy")
    dummy = DummyModule(
        {
            "actions": [
                {
                    "name": "Allow",
                    "type": "allow",
                    "code": 403,
                    "headers": [],
                    "body": {},
                }
            ]
        }
    )
    with pytest.raises(FailJsonCalled) as exc:
        module.validate_action_options(dummy)
    assert "does not support: code, headers, body." in exc.value.payload["msg"]


@pytest.mark.parametrize("action_type", ("allow", "check", "return_http_response"))
def test_valid_actions_pass_validation_and_build_models(action_type):
    """Accept valid actions with the optional null fields supplied by Ansible."""
    import oci

    module = load_collection_module("oci_waf_web_app_firewall_policy")
    action = {
        "name": "Action",
        "type": action_type,
        "code": 403 if action_type == "return_http_response" else None,
        "headers": None,
        "body": None,
    }
    module.validate_action_options(DummyModule({"actions": [action]}))
    details = module.build_create_web_app_firewall_policy_details({"actions": [action]})
    assert isinstance(details.actions[0], oci.waf.models.Action)
    assert details.actions[0].type == action_type.upper()
