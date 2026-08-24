from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

from conftest import (
    FakeModel,
    FakeResponse,
    install_fake_oci as shared_install_fake_oci,
    load_collection_module,
    make_module_instance,
)


LPG_MODEL_NAMES = (
    "CreateLocalPeeringGatewayDetails",
    "UpdateLocalPeeringGatewayDetails",
    "ConnectLocalPeeringGatewaysDetails",
)


def install_fake_oci(monkeypatch):
    return shared_install_fake_oci(
        monkeypatch,
        model_names=LPG_MODEL_NAMES,
    )


def make_lpg_module(module_obj, params, client=None):
    return make_module_instance(
        module_obj,
        "OciNetworkLocalPeeringGatewayModule",
        params,
        client=client,
    )


def test_main_exposes_peer_id_argument(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_network_local_peering_gateway")
    captured = {}

    class FakeLpgModule:
        def __init__(self, module):
            self.module = module

        def execute_resource_module(self):
            captured["run_called"] = True

    def fake_ansible_module(**kwargs):
        captured["argument_spec"] = kwargs["argument_spec"]

        class Dummy:
            params = {}

        return Dummy()

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciNetworkLocalPeeringGatewayModule", FakeLpgModule)

    module_obj.main()

    assert captured["run_called"] is True
    assert captured["argument_spec"]["peer_id"] == {"type": "str"}
    assert captured["argument_spec"]["route_table_id"] == {"type": "str"}
    assert captured["argument_spec"]["local_peering_gateway_id"] == {"type": "str"}


def test_build_create_local_peering_gateway_details_includes_supported_fields(monkeypatch):
    install_fake_oci(monkeypatch)

    lpg_module = load_collection_module("oci_network_local_peering_gateway")
    details = lpg_module.build_create_local_peering_gateway_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "name": "example-lpg",
            "route_table_id": "ocid1.routetable.oc1..example",
            "freeform_tags": {"env": "dev"},
            "defined_tags": {"Operations": {"CostCenter": "42"}},
        }
    )

    assert isinstance(details, FakeModel)
    assert details.compartment_id == "ocid1.compartment.oc1..example"
    assert details.vcn_id == "ocid1.vcn.oc1..example"
    assert details.display_name == "example-lpg"
    assert details.route_table_id == "ocid1.routetable.oc1..example"
    assert details.freeform_tags == {"env": "dev"}
    assert details.defined_tags == {"Operations": {"CostCenter": "42"}}
    assert not hasattr(details, "peer_id")


def test_needs_update_returns_false_when_peer_id_matches(monkeypatch):
    install_fake_oci(monkeypatch)

    lpg_module = load_collection_module("oci_network_local_peering_gateway")
    instance = make_lpg_module(
        lpg_module,
        {"peer_id": "ocid1.localpeeringgateway.oc1..peer"},
    )
    resource = FakeModel(
        id="ocid1.localpeeringgateway.oc1..example",
        peer_id="ocid1.localpeeringgateway.oc1..peer",
    )

    assert instance.needs_update(resource) is False


def test_needs_update_returns_true_when_peer_id_differs(monkeypatch):
    install_fake_oci(monkeypatch)

    lpg_module = load_collection_module("oci_network_local_peering_gateway")
    instance = make_lpg_module(
        lpg_module,
        {"peer_id": "ocid1.localpeeringgateway.oc1..peer"},
    )
    resource = FakeModel(
        id="ocid1.localpeeringgateway.oc1..example",
        peer_id=None,
    )

    assert instance.needs_update(resource) is True


def test_needs_update_returns_true_for_name_change(monkeypatch):
    install_fake_oci(monkeypatch)

    lpg_module = load_collection_module("oci_network_local_peering_gateway")
    instance = make_lpg_module(
        lpg_module,
        {"name": "updated-lpg"},
    )
    resource = FakeModel(
        id="ocid1.localpeeringgateway.oc1..example",
        display_name="current-lpg",
    )

    assert instance.needs_update(resource) is True


def test_update_resource_connects_peer_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)

    lpg_module = load_collection_module("oci_network_local_peering_gateway")
    connect_calls = []

    def connect_local_peering_gateways(local_peering_gateway_id, connect_local_peering_gateways_details):
        connect_calls.append((local_peering_gateway_id, connect_local_peering_gateways_details))
        return FakeResponse(data=FakeModel(id=local_peering_gateway_id))

    resource = FakeModel(id="ocid1.localpeeringgateway.oc1..example", peer_id=None)
    instance = make_lpg_module(
        lpg_module,
        {"peer_id": "ocid1.localpeeringgateway.oc1..peer", "wait": True},
        client=types.SimpleNamespace(
            connect_local_peering_gateways=connect_local_peering_gateways
        ),
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, target_states, **kwargs: FakeModel(
            id=resource_id,
            peer_id="ocid1.localpeeringgateway.oc1..peer",
            lifecycle_state="AVAILABLE",
        ),
    )

    updated_resource = instance.update_resource(resource)

    assert connect_calls[0][0] == "ocid1.localpeeringgateway.oc1..example"
    assert connect_calls[0][1].peer_id == "ocid1.localpeeringgateway.oc1..peer"
    assert updated_resource.peer_id == "ocid1.localpeeringgateway.oc1..peer"


def test_update_resource_applies_name_change_after_no_peer_drift(monkeypatch):
    install_fake_oci(monkeypatch)

    lpg_module = load_collection_module("oci_network_local_peering_gateway")
    update_calls = []

    def update_local_peering_gateway(local_peering_gateway_id, update_local_peering_gateway_details):
        update_calls.append((local_peering_gateway_id, update_local_peering_gateway_details))
        return FakeResponse(data=FakeModel(id=local_peering_gateway_id))

    resource = FakeModel(
        id="ocid1.localpeeringgateway.oc1..example",
        display_name="current-lpg",
        peer_id="ocid1.localpeeringgateway.oc1..peer",
    )
    instance = make_lpg_module(
        lpg_module,
        {
            "name": "updated-lpg",
            "peer_id": "ocid1.localpeeringgateway.oc1..peer",
            "wait": True,
        },
        client=types.SimpleNamespace(
            update_local_peering_gateway=update_local_peering_gateway
        ),
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, target_states, **kwargs: FakeModel(
            id=resource_id,
            lifecycle_state="AVAILABLE",
        ),
    )

    instance.update_resource(resource)

    assert update_calls[0][0] == "ocid1.localpeeringgateway.oc1..example"
    assert update_calls[0][1].display_name == "updated-lpg"


def test_delete_resource_uses_local_peering_gateway_id_kwarg(monkeypatch):
    install_fake_oci(monkeypatch)

    lpg_module = load_collection_module("oci_network_local_peering_gateway")
    delete_calls = []

    def delete_local_peering_gateway(**kwargs):
        delete_calls.append(kwargs)
        return FakeResponse(data=FakeModel(id="ocid1.localpeeringgateway.oc1..example"))

    resource = FakeModel(id="ocid1.localpeeringgateway.oc1..example")
    instance = make_lpg_module(
        lpg_module,
        {"wait": True},
        client=types.SimpleNamespace(
            delete_local_peering_gateway=delete_local_peering_gateway
        ),
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, target_states, **kwargs: None,
    )

    instance.delete_resource(resource)

    assert delete_calls == [{"local_peering_gateway_id": "ocid1.localpeeringgateway.oc1..example"}]
