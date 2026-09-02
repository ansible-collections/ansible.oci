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


public_ip_model_names = (
    "CreatePublicIpDetails",
    "GetPublicIpByPrivateIpIdDetails",
    "UpdatePublicIpDetails",
)


def install_fake_oci(monkeypatch):
    return shared_install_fake_oci(
        monkeypatch,
        model_names=public_ip_model_names,
    )


def make_public_ip_module(module_obj, params, client=None):
    return make_module_instance(
        module_obj,
        "OciNetworkPublicIpModule",
        params,
        client=client,
    )


def test_main_exposes_lowercase_snake_case_arguments(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_public_ip")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured.update(kwargs)
        return DummyModule({})

    class FakePublicIpModule:
        def __init__(self, module):
            self.module = module

        def execute_resource_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciNetworkPublicIpModule", FakePublicIpModule)

    module_obj.main()

    argument_spec = captured["argument_spec"]
    assert captured["run_called"] is True
    assert captured["supports_check_mode"] is True
    assert argument_spec["lifetime"]["choices"] == ["ephemeral", "reserved"]
    assert argument_spec["public_ip_id"] == {"type": "str"}
    assert argument_spec["private_ip_id"] == {"type": "str"}
    assert argument_spec["public_ip_pool_id"] == {"type": "str"}
    assert "scope" not in argument_spec
    assert "display_name" not in argument_spec


def test_build_create_details_maps_name_and_normalizes_lifetime(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_public_ip")

    details = module_obj.build_create_public_ip_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": "application-public-ip",
            "lifetime": "reserved",
            "private_ip_id": "ocid1.privateip.oc1..example",
            "public_ip_pool_id": "ocid1.publicippool.oc1..example",
            "freeform_tags": {"phase": "create"},
            "defined_tags": {"Operations": {"CostCenter": "42"}},
        }
    )

    assert details.compartment_id == "ocid1.compartment.oc1..example"
    assert details.display_name == "application-public-ip"
    assert details.lifetime == "RESERVED"
    assert details.private_ip_id == "ocid1.privateip.oc1..example"
    assert details.public_ip_pool_id == "ocid1.publicippool.oc1..example"
    assert details.freeform_tags == {"phase": "create"}
    assert details.defined_tags == {"Operations": {"CostCenter": "42"}}


def test_reserved_name_lookup_maps_filters_to_oci_enums(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_public_ip")
    list_method = object()
    list_calls = []
    instance = make_public_ip_module(
        module_obj,
        {
            "name": "application-public-ip",
            "compartment_id": "ocid1.compartment.oc1..example",
            "lifetime": "reserved",
            "public_ip_pool_id": "ocid1.publicippool.oc1..example",
        },
        client=types.SimpleNamespace(list_public_ips=list_method),
    )

    def list_all_resources(method, **kwargs):
        list_calls.append((method, kwargs))
        return [
            FakeModel(
                id="matching",
                display_name="application-public-ip",
                lifecycle_state="AVAILABLE",
            ),
            FakeModel(
                id="other",
                display_name="other-public-ip",
                lifecycle_state="AVAILABLE",
            ),
            FakeModel(
                id="deleted",
                display_name="application-public-ip",
                lifecycle_state="DELETED",
            ),
        ]

    monkeypatch.setattr(instance, "list_all_resources", list_all_resources)

    matches = instance.find_resources_by_name()

    assert [resource.id for resource in matches] == ["matching"]
    assert list_calls == [
        (
            list_method,
            {
                "scope": "REGION",
                "compartment_id": "ocid1.compartment.oc1..example",
                "lifetime": "RESERVED",
                "public_ip_pool_id": "ocid1.publicippool.oc1..example",
            },
        )
    ]


def test_ephemeral_name_lookup_uses_private_ip(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_public_ip")
    calls = []

    def get_public_ip_by_private_ip_id(**kwargs):
        calls.append(kwargs)
        return FakeResponse(
            data=FakeModel(
                id="ocid1.publicip.oc1..example",
                display_name="application-public-ip",
                lifecycle_state="ASSIGNED",
            )
        )

    instance = make_public_ip_module(
        module_obj,
        {
            "name": "application-public-ip",
            "lifetime": "ephemeral",
            "private_ip_id": "ocid1.privateip.oc1..example",
        },
        client=types.SimpleNamespace(
            get_public_ip_by_private_ip_id=get_public_ip_by_private_ip_id,
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    matches = instance.find_resources_by_name()

    assert [resource.id for resource in matches] == [
        "ocid1.publicip.oc1..example"
    ]
    details = calls[0]["get_public_ip_by_private_ip_id_details"]
    assert details.private_ip_id == "ocid1.privateip.oc1..example"


def test_ephemeral_name_lookup_handles_not_found(monkeypatch):
    service_error = install_fake_oci(monkeypatch)[1]
    module_obj = load_collection_module("oci_network_public_ip")

    def get_public_ip_by_private_ip_id(**kwargs):
        raise service_error(404)

    instance = make_public_ip_module(
        module_obj,
        {
            "name": "application-public-ip",
            "lifetime": "ephemeral",
            "private_ip_id": "ocid1.privateip.oc1..example",
        },
        client=types.SimpleNamespace(
            get_public_ip_by_private_ip_id=get_public_ip_by_private_ip_id,
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    assert instance.find_resources_by_name() == []


@pytest.mark.parametrize(
    "params,expected_message",
    [
        ({"name": "application-public-ip", "lifetime": "reserved"}, "compartment_id"),
        (
            {
                "name": "application-public-ip",
                "compartment_id": "ocid1.compartment.oc1..example",
            },
            "lifetime",
        ),
        (
            {
                "name": "application-public-ip",
                "compartment_id": "ocid1.compartment.oc1..example",
                "lifetime": "ephemeral",
            },
            "private_ip_id",
        ),
        (
            {
                "name": "application-public-ip",
                "compartment_id": "ocid1.compartment.oc1..example",
                "lifetime": "ephemeral",
                "private_ip_id": "ocid1.privateip.oc1..example",
                "allow_duplicate_name": True,
            },
            "allow_duplicate_name",
        ),
    ],
)
def test_create_validation_requires_expected_fields(
    monkeypatch, params, expected_message
):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_public_ip")
    instance = make_public_ip_module(module_obj, params)

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.validate_create_request()

    assert expected_message in exc_info.value.payload["msg"]


@pytest.mark.parametrize(
    "params,expected_message",
    [
        ({"name": "application-public-ip"}, "lifetime"),
        (
            {"name": "application-public-ip", "lifetime": "reserved"},
            "compartment_id",
        ),
        (
            {"name": "application-public-ip", "lifetime": "ephemeral"},
            "private_ip_id",
        ),
    ],
)
def test_name_lookup_validation_requires_lifetime_specific_scope(
    monkeypatch, params, expected_message
):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_public_ip")
    instance = make_public_ip_module(module_obj, params)

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.validate_name_lookup_scope()

    assert expected_message in exc_info.value.payload["msg"]


def test_update_plan_maps_mutable_fields(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_public_ip")
    instance = make_public_ip_module(
        module_obj,
        {
            "name": "application-public-ip-updated",
            "private_ip_id": "ocid1.privateip.oc1..updated",
            "freeform_tags": {"phase": "update"},
        },
    )
    resource = FakeModel(
        display_name="application-public-ip",
        assigned_entity_id=None,
        lifetime="RESERVED",
        freeform_tags={"phase": "create"},
    )

    update_plan = instance.build_update_plan(resource)
    details = instance.build_update_details(update_plan["update_model_fields"])

    assert update_plan["update_needed"] is True
    assert details.display_name == "application-public-ip-updated"
    assert details.private_ip_id == "ocid1.privateip.oc1..updated"
    assert details.freeform_tags == {"phase": "update"}


def test_lifetime_comparison_maps_lowercase_to_oci_value(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_public_ip")
    instance = make_public_ip_module(module_obj, {"lifetime": "reserved"})

    assert instance.needs_update(FakeModel(lifetime="RESERVED")) is False


@pytest.mark.parametrize(
    "field,current,desired",
    [
        (
            "compartment_id",
            "ocid1.compartment.oc1..current",
            "ocid1.compartment.oc1..desired",
        ),
        ("lifetime", "RESERVED", "ephemeral"),
        (
            "public_ip_pool_id",
            "ocid1.publicippool.oc1..current",
            "ocid1.publicippool.oc1..desired",
        ),
    ],
)
def test_update_rejects_immutable_fields(monkeypatch, field, current, desired):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_public_ip")
    instance = make_public_ip_module(module_obj, {field: desired})

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(FakeModel(**{field: current}))

    assert field in exc_info.value.payload["msg"]


def test_update_rejects_moving_ephemeral_public_ip(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_public_ip")
    instance = make_public_ip_module(
        module_obj,
        {"private_ip_id": "ocid1.privateip.oc1..desired"},
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(
            FakeModel(
                assigned_entity_id="ocid1.privateip.oc1..current",
                lifetime="EPHEMERAL",
            )
        )

    assert "ephemeral" in exc_info.value.payload["msg"]


def test_crud_calls_use_public_ip_sdk_models_and_waiters(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_public_ip")
    calls = []
    created_resource = FakeModel(id="ocid1.publicip.oc1..example")
    updated_resource = FakeModel(
        id="ocid1.publicip.oc1..example",
        display_name="application-public-ip-updated",
    )

    def get_public_ip(**kwargs):
        calls.append(("get", kwargs))
        return FakeResponse(data=created_resource)

    def create_public_ip(**kwargs):
        calls.append(("create", kwargs))
        return FakeResponse(data=created_resource)

    def update_public_ip(**kwargs):
        calls.append(("update", kwargs))
        return FakeResponse(data=updated_resource)

    def delete_public_ip(**kwargs):
        calls.append(("delete", kwargs))
        return FakeResponse(data=None)

    client = types.SimpleNamespace(
        get_public_ip=get_public_ip,
        create_public_ip=create_public_ip,
        update_public_ip=update_public_ip,
        delete_public_ip=delete_public_ip,
    )
    instance = make_public_ip_module(
        module_obj,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": "application-public-ip-updated",
            "lifetime": "reserved",
            "wait": True,
        },
        client=client,
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    wait_calls = []

    def wait_for_resource_id(resource_id, target_states, **kwargs):
        wait_calls.append((resource_id, target_states))
        if set(target_states) == {"DELETED", "TERMINATED"}:
            return None
        return updated_resource

    monkeypatch.setattr(instance, "wait_for_resource_id", wait_for_resource_id)

    response = instance.get_resource_response(created_resource.id)
    created = instance.create_resource()
    current = FakeModel(
        id=created_resource.id,
        display_name="application-public-ip",
        compartment_id="ocid1.compartment.oc1..example",
        lifetime="RESERVED",
    )
    updated = instance.update_resource(current)
    deleted = instance.delete_resource(updated)

    assert response.data.id == created_resource.id
    assert created is updated_resource
    assert updated is updated_resource
    assert deleted is None
    assert calls[0] == ("get", {"public_ip_id": created_resource.id})
    assert calls[1][0] == "create"
    assert calls[1][1]["create_public_ip_details"].lifetime == "RESERVED"
    assert calls[2][0] == "update"
    assert calls[2][1]["public_ip_id"] == created_resource.id
    assert calls[3] == ("delete", {"public_ip_id": created_resource.id})
    assert wait_calls[:2] == [
        (created_resource.id, module_obj.public_ip_ready_states),
        (created_resource.id, module_obj.public_ip_ready_states),
    ]
    assert wait_calls[2][0] == created_resource.id
    assert set(wait_calls[2][1]) == {"DELETED", "TERMINATED"}


def test_result_serialization_maps_display_name_to_name(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_public_ip")
    instance = make_public_ip_module(module_obj, {})

    result = instance.serialize_result_resource(
        FakeModel(
            id="ocid1.publicip.oc1..example",
            display_name="application-public-ip",
            lifetime="RESERVED",
        )
    )

    assert result == {
        "id": "ocid1.publicip.oc1..example",
        "name": "application-public-ip",
        "lifetime": "RESERVED",
    }
