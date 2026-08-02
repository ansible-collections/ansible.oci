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


ROUTE_TABLE_MODEL_NAMES = (
    "CreateRouteTableDetails",
    "UpdateRouteTableDetails",
    "RouteRule",
)


def install_fake_oci(monkeypatch):
    return shared_install_fake_oci(
        monkeypatch,
        model_names=ROUTE_TABLE_MODEL_NAMES,
    )


def make_route_table_module(module_obj, params, client=None):
    return make_module_instance(
        module_obj,
        "OciRouteTableModule",
        params,
        client=client,
    )


def test_main_exposes_route_rules_argument(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_route_table")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured["argument_spec"] = kwargs["argument_spec"]
        return DummyModule({})

    class FakeRouteTableModule:
        def __init__(self, module):
            self.module = module

        def execute_resource_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciRouteTableModule", FakeRouteTableModule)

    module_obj.main()

    assert captured["run_called"] is True
    assert captured["argument_spec"]["route_table_id"] == {"type": "str"}
    assert captured["argument_spec"]["vcn_id"] == {"type": "str"}
    assert "options" in captured["argument_spec"]["route_rules"]


def test_build_create_route_table_details_includes_supported_fields(monkeypatch):
    install_fake_oci(monkeypatch)

    route_table_module = load_collection_module("oci_route_table")
    details = route_table_module.build_create_route_table_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "name": "example-route-table",
            "route_rules": [
                {
                    "destination": "0.0.0.0/0",
                    "destination_type": "CIDR_BLOCK",
                    "network_entity_id": "ocid1.internetgateway.oc1..example",
                    "description": "default route",
                }
            ],
            "freeform_tags": {"env": "dev"},
            "defined_tags": {"Operations": {"CostCenter": "42"}},
        }
    )

    assert isinstance(details, FakeModel)
    assert details.compartment_id == "ocid1.compartment.oc1..example"
    assert details.vcn_id == "ocid1.vcn.oc1..example"
    assert details.display_name == "example-route-table"
    assert len(details.route_rules) == 1
    assert details.route_rules[0].destination == "0.0.0.0/0"
    assert details.route_rules[0].destination_type == "CIDR_BLOCK"
    assert details.route_rules[0].network_entity_id == "ocid1.internetgateway.oc1..example"
    assert details.route_rules[0].description == "default route"
    assert details.freeform_tags == {"env": "dev"}
    assert details.defined_tags == {"Operations": {"CostCenter": "42"}}


def test_get_resource_response_uses_rt_id_kwarg(monkeypatch):
    install_fake_oci(monkeypatch)

    route_table_module = load_collection_module("oci_route_table")
    get_calls = []

    def get_route_table(**kwargs):
        get_calls.append(kwargs)
        return FakeResponse(data=FakeModel(id=kwargs["rt_id"]))

    instance = make_route_table_module(
        route_table_module,
        {},
        client=types.SimpleNamespace(get_route_table=get_route_table),
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )

    resource = instance.get_resource_response("ocid1.routetable.oc1..example").data

    assert resource.id == "ocid1.routetable.oc1..example"
    assert get_calls == [{"rt_id": "ocid1.routetable.oc1..example"}]


def test_needs_update_returns_false_when_route_rules_match_regardless_of_order(monkeypatch):
    install_fake_oci(monkeypatch)

    route_table_module = load_collection_module("oci_route_table")
    instance = make_route_table_module(
        route_table_module,
        {
            "route_rules": [
                {
                    "destination": "10.0.0.0/16",
                    "destination_type": "CIDR_BLOCK",
                    "network_entity_id": "ocid1.natgateway.oc1..example",
                    "description": None,
                },
                {
                    "destination": "0.0.0.0/0",
                    "destination_type": "CIDR_BLOCK",
                    "network_entity_id": "ocid1.internetgateway.oc1..example",
                    "description": None,
                },
            ]
        },
    )
    resource = FakeModel(
        id="ocid1.routetable.oc1..example",
        route_rules=[
            {
                "destination": "0.0.0.0/0",
                "destination_type": "CIDR_BLOCK",
                "network_entity_id": "ocid1.internetgateway.oc1..example",
                "description": None,
                "route_type": "STATIC",
            },
            {
                "destination": "10.0.0.0/16",
                "destination_type": "CIDR_BLOCK",
                "network_entity_id": "ocid1.natgateway.oc1..example",
                "description": None,
                "route_type": "STATIC",
            },
        ],
    )

    assert instance.needs_update(resource) is False


def test_needs_update_returns_true_when_route_rules_change(monkeypatch):
    install_fake_oci(monkeypatch)

    route_table_module = load_collection_module("oci_route_table")
    instance = make_route_table_module(
        route_table_module,
        {
            "route_rules": [
                {
                    "destination": "0.0.0.0/0",
                    "destination_type": "CIDR_BLOCK",
                    "network_entity_id": "ocid1.natgateway.oc1..example",
                    "description": None,
                },
            ]
        },
    )
    resource = FakeModel(
        id="ocid1.routetable.oc1..example",
        route_rules=[
            {
                "destination": "0.0.0.0/0",
                "destination_type": "CIDR_BLOCK",
                "network_entity_id": "ocid1.internetgateway.oc1..example",
                "description": None,
                "route_type": "STATIC",
            },
        ],
    )

    assert instance.needs_update(resource) is True


def test_needs_update_returns_true_for_name_change(monkeypatch):
    install_fake_oci(monkeypatch)

    route_table_module = load_collection_module("oci_route_table")
    instance = make_route_table_module(
        route_table_module,
        {"name": "updated-route-table"},
    )
    resource = FakeModel(
        id="ocid1.routetable.oc1..example",
        display_name="current-route-table",
    )

    assert instance.needs_update(resource) is True


def test_needs_update_rejects_vcn_drift(monkeypatch):
    install_fake_oci(monkeypatch)

    route_table_module = load_collection_module("oci_route_table")
    instance = make_route_table_module(
        route_table_module,
        {"vcn_id": "ocid1.vcn.oc1..desired"},
    )
    resource = FakeModel(
        id="ocid1.routetable.oc1..example",
        vcn_id="ocid1.vcn.oc1..current",
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "vcn_id" in exc_info.value.payload["msg"]


def test_create_resource_uses_create_route_table_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)

    route_table_module = load_collection_module("oci_route_table")
    create_calls = []
    response = FakeResponse(data=FakeModel(id="ocid1.routetable.oc1..example"))

    def create_route_table(create_route_table_details):
        create_calls.append(create_route_table_details)
        return response

    instance = make_route_table_module(
        route_table_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "name": "example-route-table",
            "route_rules": [
                {
                    "destination": "0.0.0.0/0",
                    "destination_type": "CIDR_BLOCK",
                    "network_entity_id": "ocid1.internetgateway.oc1..example",
                    "description": None,
                },
            ],
            "wait": True,
        },
        client=types.SimpleNamespace(create_route_table=create_route_table),
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

    assert create_calls[0].display_name == "example-route-table"
    assert len(create_calls[0].route_rules) == 1
    assert resource.id == "ocid1.routetable.oc1..example"
    assert resource.lifecycle_state == "AVAILABLE"


def test_update_resource_replaces_route_rules_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)

    route_table_module = load_collection_module("oci_route_table")
    update_calls = []
    response = FakeResponse(data=FakeModel(id="ocid1.routetable.oc1..example"))

    def update_route_table(rt_id, update_route_table_details):
        update_calls.append((rt_id, update_route_table_details))
        return response

    resource = FakeModel(
        id="ocid1.routetable.oc1..example",
        route_rules=[],
    )
    instance = make_route_table_module(
        route_table_module,
        {
            "route_rules": [
                {
                    "destination": "0.0.0.0/0",
                    "destination_type": "CIDR_BLOCK",
                    "network_entity_id": "ocid1.internetgateway.oc1..example",
                    "description": None,
                },
            ],
            "wait": True,
        },
        client=types.SimpleNamespace(update_route_table=update_route_table),
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

    assert update_calls[0][0] == "ocid1.routetable.oc1..example"
    assert len(update_calls[0][1].route_rules) == 1
    assert update_calls[0][1].route_rules[0].destination == "0.0.0.0/0"
    assert updated_resource.id == "ocid1.routetable.oc1..example"


def test_delete_resource_uses_rt_id_kwarg(monkeypatch):
    install_fake_oci(monkeypatch)

    route_table_module = load_collection_module("oci_route_table")
    delete_calls = []
    response = FakeResponse(data=FakeModel(id="ocid1.routetable.oc1..example"))

    def delete_route_table(**kwargs):
        delete_calls.append(kwargs)
        return response

    resource = FakeModel(id="ocid1.routetable.oc1..example")
    instance = make_route_table_module(
        route_table_module,
        {"wait": True},
        client=types.SimpleNamespace(delete_route_table=delete_route_table),
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

    assert delete_calls == [{"rt_id": "ocid1.routetable.oc1..example"}]
