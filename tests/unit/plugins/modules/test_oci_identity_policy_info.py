from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import pytest

from .conftest import (
    DummyModule,
    ExitJsonCalled,
    FakeModel,
    FakeResponse,
    install_fake_oci,
    load_collection_module,
    make_module_instance,
    raising,
)


def load_policy_info_module(monkeypatch):
    """Load the policy info module with a fake OCI SDK."""
    install_fake_oci(monkeypatch)
    return load_collection_module("oci_identity_policy_info")


def make_policy_info(module_obj, params, client=None):
    """Create an info module instance without initializing OCI credentials."""
    return make_module_instance(
        module_obj,
        "OciIdentityPolicyInfoModule",
        params,
        client=client,
    )


def test_main_arguments_and_lowercase_lifecycle_choices(monkeypatch):
    """Expose policy ID, compartment filters, and lifecycle choices."""
    module_obj = load_policy_info_module(monkeypatch)
    captured = {}
    monkeypatch.setattr(
        module_obj,
        "AnsibleModule",
        lambda **kwargs: captured.update(kwargs) or DummyModule({}),
    )
    monkeypatch.setattr(
        module_obj,
        "OciIdentityPolicyInfoModule",
        lambda module: types.SimpleNamespace(execute_info_module=lambda: None),
    )
    module_obj.main()
    assert captured["required_one_of"] == [["compartment_id", "policy_id"]]
    spec = captured["argument_spec"]
    assert spec["policy_id"] == {"type": "str"}
    assert spec["compartment_id"] == {"type": "str"}
    assert spec["name"] == {"type": "str"}
    assert spec["lifecycle_state"]["choices"] == [
        "creating",
        "active",
        "inactive",
        "deleting",
        "deleted",
    ]
    assert captured["supports_check_mode"] is True


def test_lifecycle_state_is_mapped_to_sdk_case(monkeypatch):
    """Map the lowercase user lifecycle state to the SDK enum value."""
    module_obj = load_policy_info_module(monkeypatch)
    module_class = module_obj.OciIdentityPolicyInfoModule
    captured = {}
    dummy = DummyModule({"compartment_id": "c", "lifecycle_state": "inactive"})
    monkeypatch.setattr(module_obj, "AnsibleModule", lambda **kwargs: dummy)
    monkeypatch.setattr(
        module_obj,
        "OciIdentityPolicyInfoModule",
        lambda module: captured.update(params=module.params)
        or types.SimpleNamespace(execute_info_module=lambda: None),
    )
    module_obj.main()
    assert captured["params"]["lifecycle_state"] == "INACTIVE"
    monkeypatch.setattr(module_obj, "OciIdentityPolicyInfoModule", module_class)


def test_get_by_id_and_serialization(monkeypatch):
    """Fetch a policy by id and serialize its returned fields."""
    module_obj = load_policy_info_module(monkeypatch)
    policy = FakeModel(
        id="policy1",
        compartment_id="compartment1",
        name="audit",
        description="audit policy",
        statements=["Allow any-user to inspect vcns"],
        lifecycle_state="ACTIVE",
        freeform_tags={"team": "security"},
        defined_tags={"Operations": {"CostCenter": "42"}},
    )
    client = types.SimpleNamespace(get_policy=object(), list_policies=object())
    instance = make_policy_info(module_obj, {"policy_id": "policy1"}, client)
    monkeypatch.setattr(
        instance,
        "get_resource_by_id",
        lambda resource_id, method, **kwargs: [policy],
    )
    assert instance.fetch_resources() == [policy]
    assert instance.resource_id_param == "policy_id"
    assert instance.results_key == "policies"
    assert instance.resource_get_method == "get_policy"
    result = instance.serialize_result_resource(policy)
    assert result["id"] == "policy1"
    assert result["compartment_id"] == "compartment1"
    assert result["name"] == "audit"
    assert result["lifecycle_state"] == "ACTIVE"
    assert result["freeform_tags"] == {"team": "security"}
    assert result["defined_tags"] == {"Operations": {"CostCenter": "42"}}


def test_name_and_lifecycle_filters_delegate_to_list_and_filter_exact_name(monkeypatch):
    """Pass list filters to OCI and filter the result by exact policy name."""
    module_obj = load_policy_info_module(monkeypatch)
    client = types.SimpleNamespace(list_policies=object())
    instance = make_policy_info(
        module_obj,
        {
            "compartment_id": "compartment1",
            "lifecycle_state": "ACTIVE",
            "name": "audit",
        },
        client,
    )
    matching = FakeModel(name="audit", id="p1")
    other = FakeModel(name="audit-old", id="p2")
    calls = []
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda method, **kwargs: calls.append((method, kwargs)) or [matching, other],
    )
    assert instance.fetch_resources() == [matching]
    assert calls == [
        (
            client.list_policies,
            {"compartment_id": "compartment1", "lifecycle_state": "ACTIVE"},
        )
    ]


def test_get_404_returns_empty_and_other_errors_propagate(monkeypatch):
    """Return no policies for a missing id and raise other OCI errors."""
    module_obj = load_policy_info_module(monkeypatch)
    instance = make_policy_info(
        module_obj, {"policy_id": "p"}, types.SimpleNamespace(get_policy=object())
    )
    missing = RuntimeError("missing")
    missing.status = 404
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        raising(missing),
    )
    assert instance.fetch_resources() == []
    forbidden = RuntimeError("forbidden")
    forbidden.status = 403
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        raising(forbidden),
    )
    with pytest.raises(RuntimeError, match="forbidden"):
        instance.fetch_resources()


def test_info_result_is_unchanged_and_reports_policies(monkeypatch):
    """Return serialized policy results with changed set to false."""
    module_obj = load_policy_info_module(monkeypatch)
    instance = make_policy_info(module_obj, {})
    monkeypatch.setattr(
        instance,
        "fetch_resources",
        lambda: [FakeModel(id="p", name="audit", lifecycle_state="ACTIVE")],
    )
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_info_module()
    assert result.value.payload["changed"] is False
    assert result.value.payload["policies"] == [
        {"id": "p", "name": "audit", "lifecycle_state": "ACTIVE"}
    ]


def test_list_pagination_delegates_to_oci_helper(monkeypatch):
    """Delegate policy pagination to the installed OCI pagination helper."""
    module_obj = load_policy_info_module(monkeypatch)
    instance = make_policy_info(module_obj, {})
    list_fn = object()
    calls = []

    def list_all_results(method, *args, **kwargs):
        """Record OCI pagination arguments and return fake policy results."""
        calls.append((method, args, kwargs))
        return FakeResponse(["first", "second"])

    call = types.SimpleNamespace(list_call_get_all_results=list_all_results)
    globals_dict = instance.list_all_resources.__func__.__globals__
    monkeypatch.setitem(
        globals_dict,
        "oci",
        types.SimpleNamespace(pagination=call),
    )
    assert instance.list_all_resources(list_fn, compartment_id="c") == [
        "first",
        "second",
    ]
    assert calls == [(list_fn, (), {"compartment_id": "c"})]
