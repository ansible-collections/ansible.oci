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


INTERNET_GATEWAY_MODEL_NAMES = (
    "CreateInternetGatewayDetails",
    "UpdateInternetGatewayDetails",
)


def install_fake_oci(monkeypatch):
    return shared_install_fake_oci(
        monkeypatch,
        model_names=INTERNET_GATEWAY_MODEL_NAMES,
    )


def make_internet_gateway_module(module_obj, params, client=None):
    return make_module_instance(
        module_obj,
        "OciInternetGatewayModule",
        params,
        client=client,
    )


def test_main_exposes_allow_duplicate_name_argument(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_internet_gateway")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured["argument_spec"] = kwargs["argument_spec"]
        return DummyModule({})

    class FakeInternetGatewayModule:
        def __init__(self, module):
            self.module = module

        def execute_resource_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciInternetGatewayModule", FakeInternetGatewayModule)

    module_obj.main()

    assert captured["run_called"] is True
    assert captured["argument_spec"]["internet_gateway_id"] == {"type": "str"}
    assert captured["argument_spec"]["vcn_id"] == {"type": "str"}
    assert captured["argument_spec"]["is_enabled"] == {"type": "bool", "default": True}
    assert captured["argument_spec"]["route_table_id"] == {"type": "str"}
    assert captured["argument_spec"]["name"] == {"type": "str"}
    assert captured["argument_spec"]["compartment_id"] == {"type": "str"}


def test_build_create_internet_gateway_details_includes_supported_fields(monkeypatch):
    install_fake_oci(monkeypatch)

    ig_module = load_collection_module("oci_internet_gateway")
    details = ig_module.build_create_internet_gateway_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "name": "example-ig",
            "is_enabled": True,
            "route_table_id": "ocid1.routetable.oc1..example",
            "freeform_tags": {"env": "dev"},
            "defined_tags": {"Operations": {"CostCenter": "42"}},
        }
    )

    assert isinstance(details, FakeModel)
    assert details.compartment_id == "ocid1.compartment.oc1..example"
    assert details.vcn_id == "ocid1.vcn.oc1..example"
    assert details.display_name == "example-ig"
    assert details.is_enabled is True
    assert details.route_table_id == "ocid1.routetable.oc1..example"
    assert details.freeform_tags == {"env": "dev"}
    assert details.defined_tags == {"Operations": {"CostCenter": "42"}}


def test_build_create_internet_gateway_details_omits_none_values(monkeypatch):
    install_fake_oci(monkeypatch)

    ig_module = load_collection_module("oci_internet_gateway")
    details = ig_module.build_create_internet_gateway_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "name": "example-ig",
            "is_enabled": None,
            "route_table_id": None,
            "freeform_tags": None,
            "defined_tags": None,
        }
    )

    assert "is_enabled" not in details.__dict__
    assert "route_table_id" not in details.__dict__


def test_needs_update_returns_true_for_name_change(monkeypatch):
    install_fake_oci(monkeypatch)

    ig_module = load_collection_module("oci_internet_gateway")
    instance = make_internet_gateway_module(
        ig_module,
        {"name": "updated-ig"},
    )
    resource = FakeModel(
        id="ocid1.internetgateway.oc1..example",
        display_name="current-ig",
    )

    assert instance.needs_update(resource) is True


def test_needs_update_returns_true_for_is_enabled_change(monkeypatch):
    install_fake_oci(monkeypatch)

    ig_module = load_collection_module("oci_internet_gateway")
    instance = make_internet_gateway_module(
        ig_module,
        {"is_enabled": False},
    )
    resource = FakeModel(
        id="ocid1.internetgateway.oc1..example",
        is_enabled=True,
    )

    assert instance.needs_update(resource) is True


def test_needs_update_returns_true_for_route_table_change(monkeypatch):
    install_fake_oci(monkeypatch)

    ig_module = load_collection_module("oci_internet_gateway")
    instance = make_internet_gateway_module(
        ig_module,
        {"route_table_id": "ocid1.routetable.oc1..desired"},
    )
    resource = FakeModel(
        id="ocid1.internetgateway.oc1..example",
        route_table_id="ocid1.routetable.oc1..current",
    )

    assert instance.needs_update(resource) is True


def test_needs_update_rejects_vcn_id_drift(monkeypatch):
    install_fake_oci(monkeypatch)

    ig_module = load_collection_module("oci_internet_gateway")
    instance = make_internet_gateway_module(
        ig_module,
        {"vcn_id": "ocid1.vcn.oc1..desired"},
    )
    resource = FakeModel(
        id="ocid1.internetgateway.oc1..example",
        vcn_id="ocid1.vcn.oc1..current",
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "vcn_id" in exc_info.value.payload["msg"]


def test_needs_update_rejects_compartment_drift(monkeypatch):
    install_fake_oci(monkeypatch)

    ig_module = load_collection_module("oci_internet_gateway")
    instance = make_internet_gateway_module(
        ig_module,
        {"compartment_id": "ocid1.compartment.oc1..desired"},
    )
    resource = FakeModel(
        id="ocid1.internetgateway.oc1..example",
        compartment_id="ocid1.compartment.oc1..current",
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "compartment_id" in exc_info.value.payload["msg"]


def test_get_resource_response_uses_ig_id_kwarg(monkeypatch):
    install_fake_oci(monkeypatch)

    ig_module = load_collection_module("oci_internet_gateway")
    get_calls = []

    def get_internet_gateway(**kwargs):
        get_calls.append(kwargs)
        return FakeResponse(data=FakeModel(id=kwargs["ig_id"]))

    instance = make_internet_gateway_module(
        ig_module,
        {},
        client=types.SimpleNamespace(get_internet_gateway=get_internet_gateway),
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )

    response = instance.get_resource_response("ocid1.internetgateway.oc1..example")

    assert get_calls == [{"ig_id": "ocid1.internetgateway.oc1..example"}]
    assert response.data.id == "ocid1.internetgateway.oc1..example"


def test_create_resource_uses_create_internet_gateway_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)

    ig_module = load_collection_module("oci_internet_gateway")
    create_calls = []
    response = FakeResponse(
        data=FakeModel(id="ocid1.internetgateway.oc1..example"),
    )

    def create_internet_gateway(create_internet_gateway_details):
        create_calls.append(create_internet_gateway_details)
        return response

    instance = make_internet_gateway_module(
        ig_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "vcn_id": "ocid1.vcn.oc1..example",
            "name": "example-ig",
            "is_enabled": True,
            "route_table_id": "ocid1.routetable.oc1..example",
            "wait": True,
        },
        client=types.SimpleNamespace(create_internet_gateway=create_internet_gateway),
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

    assert create_calls[0].display_name == "example-ig"
    assert create_calls[0].is_enabled is True
    assert create_calls[0].route_table_id == "ocid1.routetable.oc1..example"
    assert resource.id == "ocid1.internetgateway.oc1..example"
    assert resource.lifecycle_state == "AVAILABLE"


def test_update_resource_uses_ig_id_kwarg_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)

    ig_module = load_collection_module("oci_internet_gateway")
    update_calls = []
    response = FakeResponse(
        data=FakeModel(id="ocid1.internetgateway.oc1..example"),
    )

    def update_internet_gateway(ig_id, update_internet_gateway_details):
        update_calls.append((ig_id, update_internet_gateway_details))
        return response

    resource = FakeModel(id="ocid1.internetgateway.oc1..example")
    instance = make_internet_gateway_module(
        ig_module,
        {
            "name": "updated-ig",
            "route_table_id": "ocid1.routetable.oc1..updated",
            "wait": True,
        },
        client=types.SimpleNamespace(update_internet_gateway=update_internet_gateway),
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

    assert update_calls[0][0] == "ocid1.internetgateway.oc1..example"
    assert update_calls[0][1].display_name == "updated-ig"
    assert update_calls[0][1].route_table_id == "ocid1.routetable.oc1..updated"
    assert updated_resource.id == "ocid1.internetgateway.oc1..example"


def test_update_resource_no_op_when_no_drift(monkeypatch):
    install_fake_oci(monkeypatch)

    ig_module = load_collection_module("oci_internet_gateway")
    instance = make_internet_gateway_module(
        ig_module,
        {},
        client=types.SimpleNamespace(),
    )
    resource = FakeModel(id="ocid1.internetgateway.oc1..example")

    assert instance.update_resource(resource) is resource


def test_delete_resource_uses_ig_id_kwarg(monkeypatch):
    install_fake_oci(monkeypatch)

    ig_module = load_collection_module("oci_internet_gateway")
    delete_calls = []
    response = FakeResponse(data=None)

    def delete_internet_gateway(**kwargs):
        delete_calls.append(kwargs)
        return response

    resource = FakeModel(id="ocid1.internetgateway.oc1..example")
    instance = make_internet_gateway_module(
        ig_module,
        {"wait": False},
        client=types.SimpleNamespace(delete_internet_gateway=delete_internet_gateway),
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )

    instance.delete_resource(resource)

    assert delete_calls == [{"ig_id": "ocid1.internetgateway.oc1..example"}]
