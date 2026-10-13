from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import oci
import pytest
from ansible.module_utils.common.arg_spec import ModuleArgumentSpecValidator

from .conftest import (
    DummyModule,
    ExitJsonCalled,
    FailJsonCalled,
    FakeModel,
    FakeResponse,
    load_collection_module,
    make_module_instance,
    raising,
)


def _load(name):
    return load_collection_module(name)


def _policy_module(params, *, check_mode=False, client=None):
    module = _load("oci_loadbalancer_routing_policy")
    return make_module_instance(
        module,
        "OciLoadBalancerRoutingPolicyModule",
        params,
        client=client or types.SimpleNamespace(),
        check_mode=check_mode,
    )


def _rule(name, path, backend_set="PoolA"):
    return {
        "name": name,
        "condition": "http.request.url.path eq '{0}'".format(path),
        "actions": [{"backend_set_name": backend_set}],
    }


def test_main_exposes_verified_routing_policy_options(monkeypatch):
    module = _load("oci_loadbalancer_routing_policy")
    captured = {}

    class FakePolicyModule:
        def __init__(self, active_module):
            self.module = active_module

        def execute_resource_module(self):
            captured["executed"] = True

    monkeypatch.setattr(
        module,
        "AnsibleModule",
        lambda **kwargs: captured.update(kwargs) or DummyModule({}),
    )
    monkeypatch.setattr(module, "OciLoadBalancerRoutingPolicyModule", FakePolicyModule)
    module.main()

    args = captured["argument_spec"]
    assert captured["supports_check_mode"] is True
    assert args["load_balancer_id"] == {"type": "str", "required": True}
    assert args["name"] == {"type": "str", "required": True}
    assert "condition_language_version" not in args
    assert args["rules"]["options"]["name"]["required"] is True
    assert args["rules"]["options"]["condition"]["required"] is True
    assert args["rules"]["options"]["actions"]["options"] == {
        "backend_set_name": {"type": "str", "required": True}
    }
    assert args["state"]["choices"] == ["present", "absent"]
    assert {"wait", "wait_timeout", "wait_interval"} <= set(args)
    assert "id" not in args and "compartment_id" not in args
    assert captured["executed"] is True

    validator = ModuleArgumentSpecValidator(args)
    valid = {
        "load_balancer_id": "lb",
        "name": "route",
        "rules": [_rule("images", "/Images")],
    }
    assert validator.validate(valid).error_messages == []
    invalid = dict(valid, condition_language_version="v1")
    assert validator.validate(invalid).error_messages
    invalid_action = dict(valid, rules=[_rule("images", "/Images")])
    invalid_action["rules"][0]["actions"][0]["name"] = "forward_to_backendset"
    assert validator.validate(invalid_action).error_messages
    invalid_action["rules"][0]["actions"][0].pop("backend_set_name")
    assert validator.validate(invalid_action).error_messages


def test_create_and_update_build_typed_nested_payloads():
    params = {
        "load_balancer_id": "lb",
        "name": "route",
        "rules": [_rule("images", "/Images", "ImagePool")],
    }
    original_rules = list(params["rules"])
    adapter = _policy_module(params)
    helper = load_collection_module("oci_loadbalancer", plugin_dir="module_utils")
    create_details = helper.build_load_balancer_model(
        "CreateRoutingPolicyDetails", adapter.module.params
    )
    assert isinstance(create_details, oci.load_balancer.models.CreateRoutingPolicyDetails)
    assert create_details.condition_language_version == "V1"
    assert isinstance(create_details.rules[0], oci.load_balancer.models.RoutingRule)
    assert isinstance(create_details.rules[0].actions[0], oci.load_balancer.models.ForwardToBackendSet)
    assert create_details.rules[0].condition == "http.request.url.path eq '/Images'"
    assert create_details.rules[0].actions[0].name == "FORWARD_TO_BACKENDSET"
    assert create_details.rules[0].actions[0].backend_set_name == "ImagePool"
    assert params["rules"] == original_rules

    current = oci.load_balancer.models.RoutingPolicy(
        name="route",
        condition_language_version="V1",
        rules=[
            oci.load_balancer.models.RoutingRule(
                name="images",
                condition="http.request.url.path eq '/Images'",
                actions=[oci.load_balancer.models.ForwardToBackendSet(backend_set_name="ImagePool")],
            )
        ],
    )
    assert adapter.needs_update(current) is False

    reordered = dict(params, rules=[_rule("documents", "/Documents"), _rule("images", "/Images", "ImagePool")])
    reordered_adapter = _policy_module(reordered)
    current.rules.append(
        oci.load_balancer.models.RoutingRule(
            name="documents",
            condition="http.request.url.path eq '/Documents'",
            actions=[oci.load_balancer.models.ForwardToBackendSet(backend_set_name="PoolA")],
        )
    )
    assert reordered_adapter.needs_update(current) is True
    plan = reordered_adapter.get_update_plan(current)
    update_details = reordered_adapter.build_update_details(plan["update_model_fields"], current)
    assert isinstance(update_details, oci.load_balancer.models.UpdateRoutingPolicyDetails)
    assert [rule.name for rule in update_details.rules] == ["documents", "images"]

    replacement_adapter = _policy_module(
        dict(params, rules=[_rule("documents", "/Documents")])
    )
    replacement_plan = replacement_adapter.get_update_plan(current)
    replacement_details = replacement_adapter.build_update_details(
        replacement_plan["update_model_fields"], current
    )
    assert [rule.name for rule in replacement_details.rules] == ["documents"]
    assert replacement_details.condition_language_version == "V1"

    removal_adapter = _policy_module(dict(params, rules=[]))
    removal_plan = removal_adapter.get_update_plan(current)
    removal_details = removal_adapter.build_update_details(
        removal_plan["update_model_fields"], current
    )
    assert removal_details.rules == []
    assert removal_details.condition_language_version == "V1"

    omitted = _policy_module({"load_balancer_id": "lb", "name": "route"})
    assert omitted.needs_update(current) is False


def test_mutation_calls_include_policy_name_and_parent_id():
    adapter = _policy_module({"load_balancer_id": "lb", "name": "route"})
    assert adapter.mutation_kwargs("create") == {"load_balancer_id": "lb"}
    assert adapter.mutation_kwargs("update") == {
        "load_balancer_id": "lb",
        "routing_policy_name": "route",
    }
    assert adapter.mutation_kwargs("delete") == {
        "load_balancer_id": "lb",
        "routing_policy_name": "route",
    }


def test_create_update_delete_send_expected_composite_arguments(monkeypatch):
    calls = []
    params = {
        "load_balancer_id": "lb",
        "name": "route",
        "rules": [_rule("images", "/Images")],
        "wait": False,
    }
    adapter = _policy_module(params)
    adapter._composite_call = lambda operation, method, **kwargs: calls.append(
        (operation, method, kwargs)
    ) or types.SimpleNamespace(data=FakeModel(name="route"))
    adapter._read_after_operation = lambda *args: FakeModel(name="route")
    adapter.create_resource()
    assert calls[-1][0:2] == ("create", "create_routing_policy_and_wait_for_state")
    assert set(calls[-1][2]) == {"load_balancer_id", "create_routing_policy_details"}
    details = calls[-1][2]["create_routing_policy_details"]
    assert isinstance(details, oci.load_balancer.models.CreateRoutingPolicyDetails)
    assert details.rules[0].actions[0].name == "FORWARD_TO_BACKENDSET"

    current = oci.load_balancer.models.RoutingPolicy(
        name="route",
        condition_language_version="V1",
        rules=[oci.load_balancer.models.RoutingRule(**_rule("images", "/old"))],
    )
    adapter.module.params["rules"] = [_rule("images", "/new")]
    adapter.update_resource(current)
    assert calls[-1][0:2] == ("update", "update_routing_policy_and_wait_for_state")
    assert calls[-1][2]["routing_policy_name"] == "route"
    assert isinstance(
        calls[-1][2]["update_routing_policy_details"],
        oci.load_balancer.models.UpdateRoutingPolicyDetails,
    )

    adapter.delete_resource(current)
    assert calls[-1][0:2] == ("delete", "delete_routing_policy_and_wait_for_state")
    assert calls[-1][2] == {"load_balancer_id": "lb", "routing_policy_name": "route"}


def test_routing_policy_mutation_uses_shared_helper_composite(monkeypatch):
    helper = load_collection_module("oci_loadbalancer", plugin_dir="module_utils")
    calls = []

    class Composite:
        def __init__(self, client):
            self.client = client

        def __getattr__(self, method_name):
            def invoke(**kwargs):
                calls.append((method_name, kwargs))
                return FakeResponse(FakeModel(name="route"))

            return invoke

    monkeypatch.setattr(
        helper.oci.load_balancer,
        "LoadBalancerClientCompositeOperations",
        Composite,
    )
    adapter = _policy_module(
        {
            "load_balancer_id": "lb",
            "name": "route",
            "rules": [_rule("images", "/Images")],
            "wait": False,
        }
    )
    adapter._read_after_operation = lambda operation: FakeModel(name="route")

    adapter.create_resource()

    assert calls[0][0] == "create_routing_policy_and_wait_for_state"
    assert calls[0][1]["load_balancer_id"] == "lb"


def test_missing_create_fields_fail_before_any_composite_call():
    adapter = _policy_module({"load_balancer_id": "lb", "name": "route"})
    with pytest.raises(FailJsonCalled):
        adapter.validate_create_request()
    adapter.module.params["rules"] = []
    adapter.validate_create_request()


def test_check_mode_reports_create_and_delete_changes_without_sdk_mutation():
    params = {
        "load_balancer_id": "lb",
        "name": "route",
        "rules": [_rule("images", "/Images")],
        "state": "present",
    }
    create = _policy_module(params, check_mode=True)
    create.resolve_target_resource = lambda: None
    with pytest.raises(ExitJsonCalled) as created:
        create.execute_resource_module()
    assert created.value.payload["changed"] is True

    delete = _policy_module(dict(params, state="absent"), check_mode=True)
    delete.resolve_target_resource = lambda: FakeModel(name="route")
    with pytest.raises(ExitJsonCalled) as deleted:
        delete.execute_resource_module()
    assert deleted.value.payload["changed"] is True


def test_check_mode_reports_rule_update_without_mutation_and_idempotency():
    current = oci.load_balancer.models.RoutingPolicy(
        name="route",
        condition_language_version="V1",
        rules=[
            oci.load_balancer.models.RoutingRule(
                name="images",
                condition="http.request.url.path eq '/Images'",
                actions=[oci.load_balancer.models.ForwardToBackendSet(backend_set_name="PoolA")],
            )
        ],
    )
    params = {
        "load_balancer_id": "lb",
        "name": "route",
        "rules": [],
        "state": "present",
    }
    check = _policy_module(params, check_mode=True)
    check.resolve_target_resource = lambda: current
    check._composite_call = lambda *args, **kwargs: pytest.fail("check mode called OCI")
    with pytest.raises(ExitJsonCalled) as changed:
        check.execute_resource_module()
    assert changed.value.payload["changed"] is True

    unchanged = _policy_module(
        {"load_balancer_id": "lb", "name": "route", "rules": [_rule("images", "/Images")]},
        check_mode=True,
    )
    unchanged.resolve_target_resource = lambda: current
    unchanged._composite_call = lambda *args, **kwargs: pytest.fail("idempotent task called OCI")
    with pytest.raises(ExitJsonCalled) as same:
        unchanged.execute_resource_module()
    assert same.value.payload["changed"] is False


@pytest.mark.parametrize("check_mode", [False, True])
@pytest.mark.parametrize("state", ["present", "absent"])
def test_normal_and_check_mode_report_idempotency_without_mutation(check_mode, state):
    current = oci.load_balancer.models.RoutingPolicy(
        name="route",
        condition_language_version="V1",
        rules=[
            oci.load_balancer.models.RoutingRule(
                name="images",
                condition="http.request.url.path eq '/Images'",
                actions=[oci.load_balancer.models.ForwardToBackendSet(backend_set_name="PoolA")],
            )
        ],
    )
    params = {"load_balancer_id": "lb", "name": "route", "state": state}
    if state == "present":
        params.update(
            rules=[_rule("images", "/Images")],
        )
    adapter = _policy_module(params, check_mode=check_mode)
    adapter.resolve_target_resource = lambda: current if state == "present" else None
    adapter._composite_call = raising(AssertionError("idempotent task called OCI"))
    with pytest.raises(ExitJsonCalled) as result:
        adapter.execute_resource_module()
    assert result.value.payload["changed"] is False


def test_info_main_exposes_parent_scope_and_check_mode(monkeypatch):
    info = _load("oci_loadbalancer_routing_policy_info")
    captured = {}

    class FakeInfoModule:
        def __init__(self, active_module):
            self.module = active_module

        def execute_info_module(self):
            captured["executed"] = True

    monkeypatch.setattr(
        info,
        "AnsibleModule",
        lambda **kwargs: captured.update(kwargs) or DummyModule({}),
    )
    monkeypatch.setattr(info, "OciLoadBalancerRoutingPolicyInfoModule", FakeInfoModule)
    info.main()
    assert captured["argument_spec"]["load_balancer_id"] == {
        "type": "str",
        "required": True,
    }
    assert captured["argument_spec"]["name"] == {"type": "str"}
    assert captured["supports_check_mode"] is True
    assert captured["executed"] is True


@pytest.mark.parametrize("status, returns_empty", [(404, True), (401, False)])
def test_info_list_handles_not_found_and_propagates_other_errors(
    monkeypatch, status, returns_empty
):
    info = _load("oci_loadbalancer_routing_policy_info")
    service_error = oci.exceptions.ServiceError(
        status, "ServiceError", {}, "list failed"
    )
    instance = make_module_instance(
        info,
        "OciLoadBalancerRoutingPolicyInfoModule",
        {"load_balancer_id": "lb", "name": None},
        client=types.SimpleNamespace(list_routing_policies=raising(service_error)),
    )
    if returns_empty:
        assert instance.fetch_resources() == []
    else:
        with pytest.raises(oci.exceptions.ServiceError):
            instance.fetch_resources()


def test_info_module_get_and_list_use_routing_policy_operations(monkeypatch):
    info = _load("oci_loadbalancer_routing_policy_info")
    policy = FakeModel(name="route")
    calls = []

    def get_routing_policy(load_balancer_id, routing_policy_name):
        calls.append(("get", load_balancer_id, routing_policy_name))
        return types.SimpleNamespace(data=policy)

    instance = make_module_instance(
        info,
        "OciLoadBalancerRoutingPolicyInfoModule",
        {"load_balancer_id": "lb", "name": "route"},
        client=types.SimpleNamespace(get_routing_policy=get_routing_policy),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    assert instance.fetch_resources() == [policy]
    assert calls == [("get", "lb", "route")]

    pages = []

    class Page:
        def __init__(self, data, next_page=None):
            self.data = data
            self.next_page = next_page
            self.has_next_page = next_page is not None
            self.status = 200
            self.headers = {}
            self.request = None

    def list_routing_policies(load_balancer_id, page=None):
        pages.append(page)
        if page is None:
            return Page([FakeModel(name="first")], "next")
        return Page([FakeModel(name="second")])

    listed = make_module_instance(
        info,
        "OciLoadBalancerRoutingPolicyInfoModule",
        {"load_balancer_id": "lb", "name": None},
        client=types.SimpleNamespace(list_routing_policies=list_routing_policies),
    )
    assert [item.name for item in listed.fetch_resources()] == ["first", "second"]
    assert pages == [None, "next"]

    result = make_module_instance(
        info,
        "OciLoadBalancerRoutingPolicyInfoModule",
        {"load_balancer_id": "lb", "name": "route"},
        client=types.SimpleNamespace(
            get_routing_policy=lambda **kwargs: types.SimpleNamespace(data=policy)
        ),
    )
    monkeypatch.setattr(result, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    with pytest.raises(ExitJsonCalled) as output:
        result.execute_info_module()
    assert output.value.payload["changed"] is False
    assert output.value.payload["routing_policies"][0]["name"] == "route"


@pytest.mark.parametrize("status, returns_empty", [(404, True), (401, False)])
def test_info_get_handles_not_found_and_propagates_other_errors(
    monkeypatch, status, returns_empty
):
    info = _load("oci_loadbalancer_routing_policy_info")
    service_error = oci.exceptions.ServiceError(
        status, "ServiceError", {}, "get failed"
    )
    instance = make_module_instance(
        info,
        "OciLoadBalancerRoutingPolicyInfoModule",
        {"load_balancer_id": "lb", "name": "route"},
        client=types.SimpleNamespace(get_routing_policy=raising(service_error)),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    if returns_empty:
        assert instance.fetch_resources() == []
    else:
        with pytest.raises(oci.exceptions.ServiceError):
            instance.fetch_resources()
