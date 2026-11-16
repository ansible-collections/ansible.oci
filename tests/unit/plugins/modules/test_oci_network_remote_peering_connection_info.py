from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

from .conftest import (
    ExitJsonCalled,
    FakeModel,
    FakeResponse,
    install_fake_oci,
    load_collection_module,
    make_module_instance,
)


def make_info_module(module_obj, params, client=None):
    """Build an RPC info module instance without creating an OCI client."""
    return make_module_instance(
        module_obj,
        "OciNetworkRemotePeeringConnectionInfoModule",
        params,
        client=client,
    )


def test_fetch_by_id_uses_get_operation(monkeypatch):
    """Verify ID lookups return one RPC and skip list calls."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_remote_peering_connection_info")
    calls = []

    def get_remote_peering_connection(**kwargs):
        calls.append(kwargs)
        return FakeResponse(data=FakeModel(id=kwargs["remote_peering_connection_id"]))

    instance = make_info_module(
        module_obj,
        {"remote_peering_connection_id": "rpc-id"},
        client=types.SimpleNamespace(get_remote_peering_connection=get_remote_peering_connection),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    resources = instance.fetch_resources()

    assert [resource.id for resource in resources] == ["rpc-id"]
    assert calls == [{"remote_peering_connection_id": "rpc-id"}]


def test_fetch_list_uses_compartment_drg_and_name_filter(monkeypatch):
    """Verify list lookups pass supported SDK filters."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_remote_peering_connection_info")
    calls = []
    resources = [FakeModel(id="rpc-id", display_name="wanted")]

    instance = make_info_module(
        module_obj,
        {"compartment_id": "compartment-id", "drg_id": "drg-id", "name": "wanted"},
        client=types.SimpleNamespace(list_remote_peering_connections="list-rpcs"),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda list_fn, **kwargs: calls.append((list_fn, kwargs)) or resources,
    )

    assert instance.fetch_resources() == resources
    assert calls == [
        (
            "list-rpcs",
            {"compartment_id": "compartment-id", "drg_id": "drg-id"},
        )
    ]


def test_execute_info_serializes_rpc_list(monkeypatch):
    """Verify info output uses the remote_peering_connections result key."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_remote_peering_connection_info")
    instance = make_info_module(module_obj, {"compartment_id": "compartment-id"})
    instance.fetch_resources = lambda: [
        FakeModel(id="rpc-id", display_name="example-rpc", lifecycle_state="AVAILABLE")
    ]

    try:
        instance.execute_info_module()
    except ExitJsonCalled as exc:
        assert exc.payload == {
            "changed": False,
            "remote_peering_connections": [
                {"id": "rpc-id", "name": "example-rpc", "lifecycle_state": "AVAILABLE"}
            ],
        }
    else:
        raise AssertionError("execute_info_module should exit")


def test_fetch_by_id_returns_empty_list_on_404(monkeypatch):
    """Verify a missing RPC does not fail an info lookup."""
    unused_oci, service_error = install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_remote_peering_connection_info")

    def get_remote_peering_connection(**kwargs):
        raise service_error(404)

    instance = make_info_module(
        module_obj,
        {"remote_peering_connection_id": "missing"},
        client=types.SimpleNamespace(get_remote_peering_connection=get_remote_peering_connection),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    assert instance.fetch_resources() == []
