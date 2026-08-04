from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

from conftest import (
    ExitJsonCalled,
    FakeModel,
    FakeResponse,
    install_fake_oci,
    load_collection_module,
    make_module_instance,
    raising,
)


def make_lpg_info_module(module_obj, params, client=None):
    return make_module_instance(
        module_obj,
        "OciLocalPeeringGatewayInfoModule",
        params,
        client=client,
    )


def test_fetch_resources_prefers_id_lookup(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_local_peering_gateway_info")

    def get_local_peering_gateway(**kwargs):
        return FakeResponse(
            data=FakeModel(
                id=kwargs["local_peering_gateway_id"],
                display_name="example-lpg",
            )
        )

    instance = make_lpg_info_module(
        info_module,
        {"local_peering_gateway_id": "ocid1.localpeeringgateway.oc1..example"},
        client=types.SimpleNamespace(
            get_local_peering_gateway=get_local_peering_gateway
        ),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        raising(AssertionError("list_all_resources should not be called")),
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )

    resources = instance.fetch_resources()

    assert len(resources) == 1
    assert resources[0].id == "ocid1.localpeeringgateway.oc1..example"


def test_fetch_resources_lists_by_compartment_and_vcn(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_local_peering_gateway_info")
    paginate_calls = []
    instance = make_lpg_info_module(
        info_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
        },
        client=types.SimpleNamespace(list_local_peering_gateways="list_method"),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda list_fn, **kwargs: paginate_calls.append((list_fn, kwargs)) or [],
    )

    resources = instance.fetch_resources()

    assert resources == []
    assert paginate_calls == [
        (
            "list_method",
            {
                "compartment_id": "ocid1.compartment.oc1..example",
                "vcn_id": "ocid1.vcn.oc1..example",
            },
        )
    ]


def test_run_returns_local_peering_gateways_key(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_local_peering_gateway_info")
    resource = FakeModel(
        id="ocid1.localpeeringgateway.oc1..example",
        display_name="example-lpg",
        lifecycle_state="AVAILABLE",
    )
    instance = make_lpg_info_module(
        info_module,
        {"compartment_id": "ocid1.compartment.oc1..example"},
    )
    monkeypatch.setattr(instance, "fetch_resources", lambda: [resource])

    try:
        instance.execute_info_module()
        raise AssertionError("execute_info_module should raise ExitJsonCalled")
    except ExitJsonCalled as exc_info:
        assert exc_info.payload == {
            "changed": False,
            "local_peering_gateways": [
                {
                    "id": "ocid1.localpeeringgateway.oc1..example",
                    "name": "example-lpg",
                    "lifecycle_state": "AVAILABLE",
                }
            ],
        }
