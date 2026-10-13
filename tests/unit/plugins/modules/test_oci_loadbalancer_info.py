from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import pytest

from ansible.module_utils.common.arg_spec import ArgumentSpecValidator

from .conftest import (
    DummyModule,
    ExitJsonCalled,
    FakeModel,
    FakeResponse,
    install_fake_oci as shared_install_fake_oci,
    load_collection_module,
    make_module_instance,
    raising,
)


def install_fake_oci(monkeypatch):
    oci_module, service_error = shared_install_fake_oci(monkeypatch)
    oci_module.load_balancer = types.SimpleNamespace(
        LoadBalancerClient=type("FakeLoadBalancerClient", (), {}),
    )
    return service_error


def test_main_requires_id_or_compartment_and_exposes_filters(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer_info")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured.update(kwargs)
        return DummyModule()

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(
        module_obj,
        "OciLoadBalancerInfoModule",
        lambda module: types.SimpleNamespace(execute_info_module=lambda: None),
    )

    module_obj.main()

    assert captured["required_one_of"] == [["load_balancer_id", "compartment_id"]]
    assert captured["argument_spec"]["load_balancer_id"] == {"type": "str"}
    assert captured["argument_spec"]["name"] == {"type": "str"}
    states = ["creating", "failed", "active", "deleting", "deleted"]
    state_spec = captured["argument_spec"]["lifecycle_state"]
    assert state_spec == {"type": "str", "choices": states}
    validator = ArgumentSpecValidator({"lifecycle_state": state_spec})
    for state in states:
        assert not validator.validate({"lifecycle_state": state}).error_messages
        assert validator.validate({"lifecycle_state": state.upper()}).error_messages
    assert validator.validate({"lifecycle_state": "unknown"}).error_messages


def test_get_by_id_returns_single_load_balancer(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer_info")
    calls = []
    resource = FakeModel(id="lb", display_name="example-lb")
    instance = make_module_instance(
        module_obj,
        "OciLoadBalancerInfoModule",
        {"load_balancer_id": "lb"},
        client=types.SimpleNamespace(
            get_load_balancer=lambda load_balancer_id: calls.append(load_balancer_id) or FakeResponse(resource)
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    assert instance.fetch_resources() == [resource]
    assert calls == ["lb"]


def test_get_by_id_404_returns_empty_list(monkeypatch):
    service_error = install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer_info")
    instance = make_module_instance(
        module_obj,
        "OciLoadBalancerInfoModule",
        {"load_balancer_id": "missing"},
        client=types.SimpleNamespace(
            get_load_balancer=raising(service_error(404, "missing"))
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    assert instance.fetch_resources() == []


@pytest.mark.parametrize("state", ["creating", "failed", "active", "deleting", "deleted"])
def test_list_uses_base_filters_for_name_and_lifecycle(monkeypatch, state):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer_info")
    calls = []
    matching = FakeModel(id="lb", display_name="example-lb", lifecycle_state=state.upper())
    other_name = FakeModel(id="other", display_name="other-lb", lifecycle_state=state.upper())
    listed = [matching, other_name]
    instance = make_module_instance(
        module_obj,
        "OciLoadBalancerInfoModule",
        {
            "compartment_id": "compartment",
            "name": "example-lb",
            "lifecycle_state": state,
        },
        client=types.SimpleNamespace(list_load_balancers="list-method"),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda list_fn, **kwargs: calls.append((list_fn, kwargs)) or listed,
    )

    assert instance.fetch_resources() == [matching]
    assert calls == [
        (
            "list-method",
            {
                "compartment_id": "compartment",
                "lifecycle_state": state.upper(),
            },
        )
    ]


def test_pagination_helper_is_used_for_load_balancer_lists(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer_info")
    pages = []
    instance = make_module_instance(
        module_obj,
        "OciLoadBalancerInfoModule",
        {"compartment_id": "compartment"},
        client=types.SimpleNamespace(list_load_balancers="list-method"),
    )

    def fake_list_all_resources(list_fn, **kwargs):
        pages.append((list_fn, kwargs))
        return [FakeModel(id="lb-1"), FakeModel(id="lb-2")]

    monkeypatch.setattr(instance, "list_all_resources", fake_list_all_resources)

    assert [resource.id for resource in instance.fetch_resources()] == ["lb-1", "lb-2"]
    assert pages == [("list-method", {"compartment_id": "compartment"})]


def test_list_propagates_service_errors(monkeypatch):
    service_error = install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer_info")
    instance = make_module_instance(
        module_obj,
        "OciLoadBalancerInfoModule",
        {"compartment_id": "compartment"},
        client=types.SimpleNamespace(
            list_load_balancers=raising(service_error(500, "failed"))
        ),
    )

    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda list_fn, **kwargs: list_fn(**kwargs),
    )

    with pytest.raises(service_error):
        instance.fetch_resources()


def test_execute_info_returns_load_balancers_with_changed_false(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_loadbalancer_info")
    instance = make_module_instance(
        module_obj,
        "OciLoadBalancerInfoModule",
        {"load_balancer_id": "lb"},
    )
    monkeypatch.setattr(
        instance,
        "fetch_resources",
        lambda: [FakeModel(id="lb", display_name="example-lb", lifecycle_state="ACTIVE")],
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_info_module()

    assert exc_info.value.payload == {
        "changed": False,
        "load_balancers": [
            {"id": "lb", "name": "example-lb", "lifecycle_state": "ACTIVE"}
        ],
    }
