from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import pytest

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
    oci_module.container_engine = types.SimpleNamespace(
        ContainerEngineClient=type("FakeContainerEngineClient", (), {}),
    )
    return service_error


def test_main_requires_id_or_compartment_and_exposes_filters(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_oke_node_pool_info")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured.update(kwargs)
        return DummyModule()

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(
        module_obj,
        "OciOkeNodePoolInfoModule",
        lambda module: types.SimpleNamespace(execute_info_module=lambda: None),
    )

    module_obj.main()

    assert captured["required_one_of"] == [["node_pool_id", "compartment_id"]]
    assert captured["argument_spec"]["node_pool_id"] == {"type": "str"}
    assert captured["argument_spec"]["cluster_id"] == {"type": "str"}
    assert captured["argument_spec"]["name"] == {"type": "str"}
    assert captured["argument_spec"]["lifecycle_state"] == {"type": "str"}


def test_get_by_id_returns_single_node_pool(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_oke_node_pool_info")
    calls = []
    resource = FakeModel(id="n1", name="example-pool")
    instance = make_module_instance(
        module_obj,
        "OciOkeNodePoolInfoModule",
        {"node_pool_id": "n1"},
        client=types.SimpleNamespace(
            get_node_pool=lambda node_pool_id: calls.append(node_pool_id)
            or FakeResponse(resource)
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    assert instance.fetch_resources() == [resource]
    assert calls == ["n1"]


def test_get_by_id_404_returns_empty_list(monkeypatch):
    service_error = install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_oke_node_pool_info")
    instance = make_module_instance(
        module_obj,
        "OciOkeNodePoolInfoModule",
        {"node_pool_id": "missing"},
        client=types.SimpleNamespace(
            get_node_pool=raising(service_error(404, "missing"))
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    assert instance.fetch_resources() == []


def test_list_filters_by_cluster_name_and_lifecycle(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_oke_node_pool_info")
    calls = []
    matching = FakeModel(id="n1", name="example-pool", lifecycle_state="ACTIVE")
    other_name = FakeModel(id="other", name="other-pool", lifecycle_state="ACTIVE")
    listed = [matching, other_name]
    instance = make_module_instance(
        module_obj,
        "OciOkeNodePoolInfoModule",
        {
            "compartment_id": "compartment",
            "cluster_id": "cluster",
            "name": "example-pool",
            "lifecycle_state": "ACTIVE",
        },
        client=types.SimpleNamespace(list_node_pools="list-method"),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda list_fn, **kwargs: calls.append((list_fn, kwargs)) or listed,
    )

    assert instance.fetch_resources() == [matching]
    # list_node_pools takes lifecycle_state as a list, so the scalar module param
    # is wrapped before being handed to the SDK.
    assert calls == [
        (
            "list-method",
            {
                "compartment_id": "compartment",
                "cluster_id": "cluster",
                "lifecycle_state": ["ACTIVE"],
            },
        )
    ]


def test_list_propagates_service_errors(monkeypatch):
    service_error = install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_oke_node_pool_info")
    instance = make_module_instance(
        module_obj,
        "OciOkeNodePoolInfoModule",
        {"compartment_id": "compartment"},
        client=types.SimpleNamespace(
            list_node_pools=raising(service_error(500, "failed"))
        ),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda list_fn, **kwargs: list_fn(**kwargs),
    )

    with pytest.raises(service_error):
        instance.fetch_resources()


def test_execute_info_returns_node_pools_with_changed_false(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_oke_node_pool_info")
    instance = make_module_instance(
        module_obj,
        "OciOkeNodePoolInfoModule",
        {"node_pool_id": "n1"},
    )
    monkeypatch.setattr(
        instance,
        "fetch_resources",
        lambda: [FakeModel(id="n1", name="example-pool", lifecycle_state="ACTIVE")],
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_info_module()

    assert exc_info.value.payload == {
        "changed": False,
        "node_pools": [
            {"id": "n1", "name": "example-pool", "lifecycle_state": "ACTIVE"}
        ],
    }
