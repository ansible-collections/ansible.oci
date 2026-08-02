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


SERVICE_GATEWAY_MODEL_NAMES = (
    "CreateServiceGatewayDetails",
    "UpdateServiceGatewayDetails",
    "ServiceIdRequestDetails",
)


def install_fake_oci(monkeypatch):
    return shared_install_fake_oci(
        monkeypatch,
        model_names=SERVICE_GATEWAY_MODEL_NAMES,
    )


def make_service_gateway_module(module_obj, params, client=None):
    return make_module_instance(
        module_obj,
        "OciServiceGatewayModule",
        params,
        client=client,
    )


def test_main_exposes_allow_duplicate_name_argument(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_service_gateway")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured["argument_spec"] = kwargs["argument_spec"]
        return DummyModule({})

    class FakeServiceGatewayModule:
        def __init__(self, module):
            self.module = module

        def execute_resource_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciServiceGatewayModule", FakeServiceGatewayModule)

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


def test_build_service_models_wraps_each_id(monkeypatch):
    install_fake_oci(monkeypatch)

    service_gateway_module = load_collection_module("oci_service_gateway")
    models = service_gateway_module.build_service_models(
        ["ocid1.service.oc1..one", "ocid1.service.oc1..two"]
    )

    assert len(models) == 2
    assert all(isinstance(model, FakeModel) for model in models)
    assert models[0].service_id == "ocid1.service.oc1..one"
    assert models[1].service_id == "ocid1.service.oc1..two"


def test_build_service_models_handles_none_and_empty():
    from ansible_collections.oracle.oci.plugins.modules.oci_service_gateway import (
        build_service_models,
    )

    assert build_service_models(None) == []
    assert build_service_models([]) == []


def test_build_create_service_gateway_details_includes_supported_fields(monkeypatch):
    install_fake_oci(monkeypatch)

    service_gateway_module = load_collection_module("oci_service_gateway")
    details = service_gateway_module.build_create_service_gateway_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "name": "example-service-gateway",
            "route_table_id": "ocid1.routetable.oc1..example",
            "service_ids": ["ocid1.service.oc1..example"],
            "freeform_tags": {"env": "dev"},
            "defined_tags": {"Operations": {"CostCenter": "42"}},
        }
    )

    assert isinstance(details, FakeModel)
    assert details.compartment_id == "ocid1.compartment.oc1..example"
    assert details.vcn_id == "ocid1.vcn.oc1..example"
    assert details.display_name == "example-service-gateway"
    assert details.route_table_id == "ocid1.routetable.oc1..example"
    assert len(details.services) == 1
    assert details.services[0].service_id == "ocid1.service.oc1..example"
    assert details.freeform_tags == {"env": "dev"}
    assert details.defined_tags == {"Operations": {"CostCenter": "42"}}
    assert not hasattr(details, "block_traffic")


def test_build_create_service_gateway_details_defaults_services_to_empty_list(monkeypatch):
    install_fake_oci(monkeypatch)

    service_gateway_module = load_collection_module("oci_service_gateway")
    details = service_gateway_module.build_create_service_gateway_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "name": "example-service-gateway",
        }
    )

    assert details.services == []


def test_build_update_plan_maps_service_gateway_fields_to_update_model(monkeypatch):
    install_fake_oci(monkeypatch)

    service_gateway_module = load_collection_module("oci_service_gateway")
    instance = make_service_gateway_module(
        service_gateway_module,
        {
            "name": "updated-service-gateway",
            "route_table_id": "ocid1.routetable.oc1..updated",
        },
    )
    resource = FakeModel(
        id="ocid1.servicegateway.oc1..example",
        display_name="current-service-gateway",
        route_table_id="ocid1.routetable.oc1..current",
        services=[],
    )

    update_plan = instance.build_update_plan(resource)

    assert update_plan["update_needed"] is True
    assert update_plan["update_model_fields"] == {
        "display_name": "updated-service-gateway",
        "route_table_id": "ocid1.routetable.oc1..updated",
    }
    assert update_plan["strategy_operations"] == []


def test_needs_update_returns_true_for_name_change(monkeypatch):
    install_fake_oci(monkeypatch)

    service_gateway_module = load_collection_module("oci_service_gateway")
    instance = make_service_gateway_module(
        service_gateway_module,
        {"name": "updated-service-gateway"},
    )
    resource = FakeModel(
        id="ocid1.servicegateway.oc1..example",
        display_name="current-service-gateway",
        services=[],
    )

    assert instance.needs_update(resource) is True


def test_needs_update_returns_true_for_route_table_change(monkeypatch):
    install_fake_oci(monkeypatch)

    service_gateway_module = load_collection_module("oci_service_gateway")
    instance = make_service_gateway_module(
        service_gateway_module,
        {"route_table_id": "ocid1.routetable.oc1..desired"},
    )
    resource = FakeModel(
        id="ocid1.servicegateway.oc1..example",
        route_table_id="ocid1.routetable.oc1..current",
        services=[],
    )

    assert instance.needs_update(resource) is True


def test_needs_update_returns_true_for_block_traffic_change(monkeypatch):
    install_fake_oci(monkeypatch)

    service_gateway_module = load_collection_module("oci_service_gateway")
    instance = make_service_gateway_module(
        service_gateway_module,
        {"block_traffic": True},
    )
    resource = FakeModel(
        id="ocid1.servicegateway.oc1..example",
        block_traffic=False,
        services=[],
    )

    assert instance.needs_update(resource) is True


def test_needs_update_rejects_vcn_drift(monkeypatch):
    install_fake_oci(monkeypatch)

    service_gateway_module = load_collection_module("oci_service_gateway")
    instance = make_service_gateway_module(
        service_gateway_module,
        {"vcn_id": "ocid1.vcn.oc1..desired"},
    )
    resource = FakeModel(
        id="ocid1.servicegateway.oc1..example",
        vcn_id="ocid1.vcn.oc1..current",
        services=[],
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "vcn_id" in exc_info.value.payload["msg"]


def test_needs_update_rejects_compartment_drift(monkeypatch):
    install_fake_oci(monkeypatch)

    service_gateway_module = load_collection_module("oci_service_gateway")
    instance = make_service_gateway_module(
        service_gateway_module,
        {"compartment_id": "ocid1.compartment.oc1..desired"},
    )
    resource = FakeModel(
        id="ocid1.servicegateway.oc1..example",
        compartment_id="ocid1.compartment.oc1..current",
        services=[],
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "compartment_id" in exc_info.value.payload["msg"]


def test_needs_update_returns_false_when_service_ids_match_regardless_of_order(monkeypatch):
    install_fake_oci(monkeypatch)

    service_gateway_module = load_collection_module("oci_service_gateway")
    instance = make_service_gateway_module(
        service_gateway_module,
        {
            "service_ids": [
                "ocid1.service.oc1..two",
                "ocid1.service.oc1..one",
            ],
        },
    )
    resource = FakeModel(
        id="ocid1.servicegateway.oc1..example",
        services=[
            {"service_id": "ocid1.service.oc1..one", "service_name": "One"},
            {"service_id": "ocid1.service.oc1..two", "service_name": "Two"},
        ],
    )

    assert instance.needs_update(resource) is False


def test_needs_update_returns_true_when_service_ids_differ(monkeypatch):
    install_fake_oci(monkeypatch)

    service_gateway_module = load_collection_module("oci_service_gateway")
    instance = make_service_gateway_module(
        service_gateway_module,
        {
            "service_ids": [
                "ocid1.service.oc1..one",
                "ocid1.service.oc1..three",
            ],
        },
    )
    resource = FakeModel(
        id="ocid1.servicegateway.oc1..example",
        services=[
            {"service_id": "ocid1.service.oc1..one", "service_name": "One"},
            {"service_id": "ocid1.service.oc1..two", "service_name": "Two"},
        ],
    )

    assert instance.needs_update(resource) is True


def test_plan_service_ids_strategy_returns_empty_when_matching(monkeypatch):
    install_fake_oci(monkeypatch)

    service_gateway_module = load_collection_module("oci_service_gateway")
    instance = make_service_gateway_module(service_gateway_module, {})
    resource_dict = {
        "services": [
            {"service_id": "ocid1.service.oc1..one", "service_name": "One"},
        ]
    }

    operations = instance.plan_service_ids_strategy(
        FakeModel(),
        resource_dict,
        {},
        ["ocid1.service.oc1..one"],
    )

    assert operations == []


def test_plan_service_ids_strategy_returns_replace_when_differing(monkeypatch):
    install_fake_oci(monkeypatch)

    service_gateway_module = load_collection_module("oci_service_gateway")
    instance = make_service_gateway_module(service_gateway_module, {})
    resource_dict = {
        "services": [
            {"service_id": "ocid1.service.oc1..one", "service_name": "One"},
        ]
    }

    operations = instance.plan_service_ids_strategy(
        FakeModel(),
        resource_dict,
        {},
        ["ocid1.service.oc1..two"],
    )

    assert operations == [("replace", ["ocid1.service.oc1..two"])]


def test_create_resource_uses_create_service_gateway_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)

    service_gateway_module = load_collection_module("oci_service_gateway")
    create_calls = []
    response = FakeResponse(
        data=FakeModel(id="ocid1.servicegateway.oc1..example"),
    )

    def create_service_gateway(create_service_gateway_details):
        create_calls.append(create_service_gateway_details)
        return response

    instance = make_service_gateway_module(
        service_gateway_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "name": "example-service-gateway",
            "route_table_id": "ocid1.routetable.oc1..example",
            "service_ids": ["ocid1.service.oc1..example"],
            "wait": True,
        },
        client=types.SimpleNamespace(create_service_gateway=create_service_gateway),
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

    assert create_calls[0].display_name == "example-service-gateway"
    assert create_calls[0].route_table_id == "ocid1.routetable.oc1..example"
    assert len(create_calls[0].services) == 1
    assert create_calls[0].services[0].service_id == "ocid1.service.oc1..example"
    assert resource.id == "ocid1.servicegateway.oc1..example"
    assert resource.lifecycle_state == "AVAILABLE"


def test_update_resource_uses_update_service_gateway_details_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)

    service_gateway_module = load_collection_module("oci_service_gateway")
    update_calls = []
    response = FakeResponse(
        data=FakeModel(id="ocid1.servicegateway.oc1..example"),
    )

    def update_service_gateway(service_gateway_id, update_service_gateway_details):
        update_calls.append((service_gateway_id, update_service_gateway_details))
        return response

    resource = FakeModel(
        id="ocid1.servicegateway.oc1..example",
        services=[{"service_id": "ocid1.service.oc1..old", "service_name": "Old"}],
    )
    instance = make_service_gateway_module(
        service_gateway_module,
        {
            "name": "updated-service-gateway",
            "service_ids": ["ocid1.service.oc1..new"],
            "freeform_tags": {"env": "prod"},
            "wait": True,
        },
        client=types.SimpleNamespace(update_service_gateway=update_service_gateway),
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

    assert update_calls[0][0] == "ocid1.servicegateway.oc1..example"
    assert update_calls[0][1].display_name == "updated-service-gateway"
    assert len(update_calls[0][1].services) == 1
    assert update_calls[0][1].services[0].service_id == "ocid1.service.oc1..new"
    assert updated_resource.id == "ocid1.servicegateway.oc1..example"


def test_update_resource_is_noop_when_nothing_changed(monkeypatch):
    install_fake_oci(monkeypatch)

    service_gateway_module = load_collection_module("oci_service_gateway")

    def fail_update_service_gateway(**kwargs):
        raise AssertionError("update_service_gateway should not be called")

    resource = FakeModel(
        id="ocid1.servicegateway.oc1..example",
        display_name="example-service-gateway",
        services=[],
    )
    instance = make_service_gateway_module(
        service_gateway_module,
        {
            "name": "example-service-gateway",
        },
        client=types.SimpleNamespace(update_service_gateway=fail_update_service_gateway),
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )

    updated_resource = instance.update_resource(resource)

    assert updated_resource is resource
