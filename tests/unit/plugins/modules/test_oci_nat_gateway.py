from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import pytest

from conftest import (
    DummyModule,
    FakeModel,
    FakeResponse,
    FailJsonCalled,
    install_fake_oci as shared_install_fake_oci,
    load_collection_module,
    make_module_instance,
)


NAT_GATEWAY_MODEL_NAMES = (
    "CreateNatGatewayDetails",
    "UpdateNatGatewayDetails",
)


def install_fake_oci(monkeypatch):
    return shared_install_fake_oci(
        monkeypatch,
        model_names=NAT_GATEWAY_MODEL_NAMES,
    )


def make_nat_gateway_module(module_obj, params, client=None):
    return make_module_instance(
        module_obj,
        "OciNatGatewayModule",
        params,
        client=client,
    )


def test_main_exposes_allow_duplicate_name_argument(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_nat_gateway")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured["argument_spec"] = kwargs["argument_spec"]
        return DummyModule({})

    class FakeNatGatewayModule:
        def __init__(self, module):
            self.module = module

        def execute_resource_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciNatGatewayModule", FakeNatGatewayModule)

    module_obj.main()

    assert captured["run_called"] is True
    assert module_obj.OCI_COMMON_ARGS["allow_duplicate_name"] == {
        "type": "bool",
        "default": False,
    }
    assert module_obj.OCI_COMMON_ARGS["name"] == {"type": "str"}
    assert module_obj.OCI_COMMON_ARGS["compartment_id"] == {"type": "str"}
    assert captured["argument_spec"]["allow_duplicate_name"] == {
        "type": "bool",
        "default": False,
    }
    assert captured["argument_spec"]["name"] == {"type": "str"}
    assert captured["argument_spec"]["compartment_id"] == {"type": "str"}
    assert "display_name" not in captured["argument_spec"]


def test_build_create_nat_gateway_details_includes_supported_fields(monkeypatch):
    install_fake_oci(monkeypatch)

    nat_gateway_module = load_collection_module("oci_nat_gateway")
    details = nat_gateway_module.build_create_nat_gateway_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "name": "example-nat-gateway",
            "block_traffic": True,
            "route_table_id": "ocid1.routetable.oc1..example",
            "public_ip_id": "ocid1.publicip.oc1..example",
            "freeform_tags": {"env": "dev"},
            "defined_tags": {"Operations": {"CostCenter": "42"}},
        }
    )

    assert isinstance(details, FakeModel)
    assert details.compartment_id == "ocid1.compartment.oc1..example"
    assert details.vcn_id == "ocid1.vcn.oc1..example"
    assert details.display_name == "example-nat-gateway"
    assert details.block_traffic is True
    assert details.route_table_id == "ocid1.routetable.oc1..example"
    assert details.public_ip_id == "ocid1.publicip.oc1..example"
    assert details.freeform_tags == {"env": "dev"}
    assert details.defined_tags == {"Operations": {"CostCenter": "42"}}


def test_build_update_plan_maps_nat_gateway_fields_to_update_model(monkeypatch):
    install_fake_oci(monkeypatch)

    nat_gateway_module = load_collection_module("oci_nat_gateway")
    instance = make_nat_gateway_module(
        nat_gateway_module,
        {
            "name": "updated-nat-gateway",
            "block_traffic": True,
            "route_table_id": "ocid1.routetable.oc1..updated",
        },
    )
    resource = FakeModel(
        id="ocid1.natgateway.oc1..example",
        display_name="current-nat-gateway",
        block_traffic=False,
        route_table_id="ocid1.routetable.oc1..current",
    )

    update_plan = instance.build_update_plan(resource)

    assert update_plan["update_needed"] is True
    assert update_plan["update_model_fields"] == {
        "display_name": "updated-nat-gateway",
        "block_traffic": True,
        "route_table_id": "ocid1.routetable.oc1..updated",
    }
    assert update_plan["strategy_operations"] == []


def test_needs_update_returns_true_for_block_traffic_change(monkeypatch):
    install_fake_oci(monkeypatch)

    nat_gateway_module = load_collection_module("oci_nat_gateway")
    instance = make_nat_gateway_module(
        nat_gateway_module,
        {"block_traffic": True},
    )
    resource = FakeModel(id="ocid1.natgateway.oc1..example", block_traffic=False)

    assert instance.needs_update(resource) is True


def test_needs_update_returns_true_for_route_table_change(monkeypatch):
    install_fake_oci(monkeypatch)

    nat_gateway_module = load_collection_module("oci_nat_gateway")
    instance = make_nat_gateway_module(
        nat_gateway_module,
        {"route_table_id": "ocid1.routetable.oc1..desired"},
    )
    resource = FakeModel(
        id="ocid1.natgateway.oc1..example",
        route_table_id="ocid1.routetable.oc1..current",
    )

    assert instance.needs_update(resource) is True


def test_needs_update_returns_true_for_name_change(monkeypatch):
    install_fake_oci(monkeypatch)

    nat_gateway_module = load_collection_module("oci_nat_gateway")
    instance = make_nat_gateway_module(
        nat_gateway_module,
        {"name": "updated-nat-gateway"},
    )
    resource = FakeModel(
        id="ocid1.natgateway.oc1..example",
        display_name="current-nat-gateway",
    )

    assert instance.needs_update(resource) is True


def test_needs_update_rejects_public_ip_id_drift(monkeypatch):
    install_fake_oci(monkeypatch)

    nat_gateway_module = load_collection_module("oci_nat_gateway")
    instance = make_nat_gateway_module(
        nat_gateway_module,
        {"public_ip_id": "ocid1.publicip.oc1..desired"},
    )
    resource = FakeModel(
        id="ocid1.natgateway.oc1..example",
        public_ip_id="ocid1.publicip.oc1..current",
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "public_ip_id" in exc_info.value.payload["msg"]


def test_needs_update_rejects_vcn_id_drift(monkeypatch):
    install_fake_oci(monkeypatch)

    nat_gateway_module = load_collection_module("oci_nat_gateway")
    instance = make_nat_gateway_module(
        nat_gateway_module,
        {"vcn_id": "ocid1.vcn.oc1..desired"},
    )
    resource = FakeModel(
        id="ocid1.natgateway.oc1..example",
        vcn_id="ocid1.vcn.oc1..current",
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "vcn_id" in exc_info.value.payload["msg"]


def test_needs_update_rejects_compartment_drift(monkeypatch):
    install_fake_oci(monkeypatch)

    nat_gateway_module = load_collection_module("oci_nat_gateway")
    instance = make_nat_gateway_module(
        nat_gateway_module,
        {"compartment_id": "ocid1.compartment.oc1..desired"},
    )
    resource = FakeModel(
        id="ocid1.natgateway.oc1..example",
        compartment_id="ocid1.compartment.oc1..current",
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "compartment_id" in exc_info.value.payload["msg"]


def test_create_resource_uses_create_nat_gateway_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)

    nat_gateway_module = load_collection_module("oci_nat_gateway")
    create_calls = []
    response = FakeResponse(
        data=FakeModel(id="ocid1.natgateway.oc1..example"),
    )

    def create_nat_gateway(create_nat_gateway_details):
        create_calls.append(create_nat_gateway_details)
        return response

    instance = make_nat_gateway_module(
        nat_gateway_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "name": "example-nat-gateway",
            "block_traffic": True,
            "route_table_id": "ocid1.routetable.oc1..example",
            "wait": True,
        },
        client=types.SimpleNamespace(create_nat_gateway=create_nat_gateway),
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

    resource = instance.create_resource()

    assert create_calls[0].display_name == "example-nat-gateway"
    assert create_calls[0].block_traffic is True
    assert create_calls[0].route_table_id == "ocid1.routetable.oc1..example"
    assert resource.id == "ocid1.natgateway.oc1..example"
    assert resource.lifecycle_state == "AVAILABLE"


def test_update_resource_uses_update_nat_gateway_details_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)

    nat_gateway_module = load_collection_module("oci_nat_gateway")
    update_calls = []
    response = FakeResponse(
        data=FakeModel(id="ocid1.natgateway.oc1..example"),
    )

    def update_nat_gateway(nat_gateway_id, update_nat_gateway_details):
        update_calls.append((nat_gateway_id, update_nat_gateway_details))
        return response

    resource = FakeModel(id="ocid1.natgateway.oc1..example")
    instance = make_nat_gateway_module(
        nat_gateway_module,
        {
            "name": "updated-nat-gateway",
            "route_table_id": "ocid1.routetable.oc1..updated",
            "freeform_tags": {"env": "prod"},
            "wait": True,
        },
        client=types.SimpleNamespace(update_nat_gateway=update_nat_gateway),
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

    updated_resource = instance.update_resource(resource)

    assert update_calls[0][0] == "ocid1.natgateway.oc1..example"
    assert update_calls[0][1].display_name == "updated-nat-gateway"
    assert update_calls[0][1].route_table_id == "ocid1.routetable.oc1..updated"
    assert updated_resource.id == "ocid1.natgateway.oc1..example"


def test_delete_resource_uses_delete_nat_gateway_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)

    nat_gateway_module = load_collection_module("oci_nat_gateway")
    delete_calls = []
    response = FakeResponse(data=None)

    def delete_nat_gateway(nat_gateway_id):
        delete_calls.append(nat_gateway_id)
        return response

    resource = FakeModel(id="ocid1.natgateway.oc1..example")
    instance = make_nat_gateway_module(
        nat_gateway_module,
        {"wait": True},
        client=types.SimpleNamespace(delete_nat_gateway=delete_nat_gateway),
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

    assert delete_calls == ["ocid1.natgateway.oc1..example"]
