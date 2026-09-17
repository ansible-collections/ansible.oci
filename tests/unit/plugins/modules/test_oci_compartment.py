from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import pytest

from .conftest import (
    DummyModule,
    FakeModel,
    FakeResponse,
    FailJsonCalled,
    install_fake_oci as shared_install_fake_oci,
    load_collection_module,
    make_module_instance,
)


COMPARTMENT_MODEL_NAMES = (
    "CreateCompartmentDetails",
    "UpdateCompartmentDetails",
)


def install_fake_oci(monkeypatch):
    return shared_install_fake_oci(
        monkeypatch,
        model_names=COMPARTMENT_MODEL_NAMES,
    )


def make_compartment_module(module_obj, params, client=None):
    return make_module_instance(
        module_obj,
        "OciCompartmentModule",
        params,
        client=client,
    )


def test_main_exposes_compartment_arguments(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_compartment")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured["argument_spec"] = kwargs["argument_spec"]
        return DummyModule({})

    class FakeCompartmentModule:
        def __init__(self, module):
            self.module = module

        def execute_resource_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciCompartmentModule", FakeCompartmentModule)

    module_obj.main()

    assert captured["run_called"] is True
    assert captured["argument_spec"]["compartment_id"] == {"type": "str"}
    assert captured["argument_spec"]["parent_compartment_id"] == {"type": "str"}
    assert captured["argument_spec"]["name"] == {"type": "str"}
    assert captured["argument_spec"]["description"] == {"type": "str"}
    assert "allow_duplicate_name" not in captured["argument_spec"]


def test_build_create_compartment_details_maps_parent_and_tags(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_compartment")

    details = module_obj.build_create_compartment_details(
        {
            "parent_compartment_id": "ocid1.compartment.oc1..parent",
            "name": "development",
            "description": "Development resources",
            "freeform_tags": {"environment": "development"},
            "defined_tags": {"Operations": {"CostCenter": "42"}},
        }
    )

    assert isinstance(details, FakeModel)
    assert details.compartment_id == "ocid1.compartment.oc1..parent"
    assert details.name == "development"
    assert details.description == "Development resources"
    assert details.freeform_tags == {"environment": "development"}
    assert details.defined_tags == {"Operations": {"CostCenter": "42"}}


def test_name_lookup_uses_parent_active_compartment_list(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_compartment")
    calls = []
    instance = make_compartment_module(
        module_obj,
        {
            "parent_compartment_id": "ocid1.compartment.oc1..parent",
            "name": "development",
        },
        client=types.SimpleNamespace(list_compartments="list_compartments_method"),
    )
    expected = [FakeModel(id="ocid1.compartment.oc1..child", name="development")]
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda list_fn, **kwargs: calls.append((list_fn, kwargs)) or expected,
    )

    assert instance.resolve_target_resource() == expected[0]
    assert calls == [
        (
            "list_compartments_method",
            {
                "compartment_id": "ocid1.compartment.oc1..parent",
                "name": "development",
                "lifecycle_state": "ACTIVE",
            },
        )
    ]


def test_name_lookup_requires_parent_compartment(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_compartment")
    instance = make_compartment_module(module_obj, {"name": "development"})

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.resolve_target_resource()

    assert "parent_compartment_id" in exc_info.value.payload["msg"]


def test_get_resource_by_id_uses_parent_scoped_list(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_compartment")
    expected = FakeModel(id="ocid1.compartment.oc1..child", name="development")
    instance = make_compartment_module(
        module_obj,
        {
            "compartment_id": "ocid1.compartment.oc1..child",
            "parent_compartment_id": "ocid1.compartment.oc1..parent",
        },
        client=types.SimpleNamespace(list_compartments="list_compartments_method"),
    )
    calls = []
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda list_fn, **kwargs: calls.append((list_fn, kwargs)) or [expected],
    )

    assert instance.get_resource_by_id("ocid1.compartment.oc1..child") == expected
    assert calls == [
        (
            "list_compartments_method",
            {"compartment_id": "ocid1.compartment.oc1..parent"},
        )
    ]


def test_parent_scoped_wait_returns_active_compartment(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_compartment")
    active = FakeModel(
        id="ocid1.compartment.oc1..child",
        lifecycle_state="ACTIVE",
    )
    not_found = RuntimeError("compartment is not ready")
    not_found.status = 404
    responses = iter((not_found, FakeResponse(data=active)))
    instance = make_compartment_module(
        module_obj,
        {
            "parent_compartment_id": "ocid1.compartment.oc1..parent",
            "wait": True,
        },
    )

    def get_resource_response(_resource_id):
        response = next(responses)
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(instance, "get_resource_response", get_resource_response)

    def wait_until(client, initial_response, **kwargs):
        assert initial_response.data is None
        final_response = kwargs["fetch_func"]()
        assert kwargs["evaluate_response"](final_response)
        return final_response

    monkeypatch.setattr(module_obj.oci, "wait_until", wait_until, raising=False)

    assert instance.wait_for_resource_id(
        "ocid1.compartment.oc1..child",
        ("ACTIVE",),
    ) == active


def test_parent_scoped_wait_returns_none_after_deletion(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_compartment")
    deleting = FakeModel(
        id="ocid1.compartment.oc1..child",
        lifecycle_state="DELETING",
    )
    not_found = RuntimeError("compartment was deleted")
    not_found.status = 404
    responses = iter((FakeResponse(data=deleting), not_found))
    instance = make_compartment_module(
        module_obj,
        {
            "parent_compartment_id": "ocid1.compartment.oc1..parent",
            "wait": True,
        },
    )

    def get_resource_response(_resource_id):
        response = next(responses)
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(instance, "get_resource_response", get_resource_response)

    def wait_until(client, initial_response, **kwargs):
        assert initial_response.data == deleting
        final_response = kwargs["fetch_func"]()
        assert kwargs["evaluate_response"](final_response)
        return final_response

    monkeypatch.setattr(module_obj.oci, "wait_until", wait_until, raising=False)

    assert instance.wait_for_resource_id(
        "ocid1.compartment.oc1..child",
        ("DELETED", "TERMINATED"),
    ) is None


def test_update_plan_includes_name_description_and_tags(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_compartment")
    instance = make_compartment_module(
        module_obj,
        {
            "name": "production",
            "description": "Production resources",
            "freeform_tags": {"environment": "production"},
            "defined_tags": {"Operations": {"CostCenter": "99"}},
        },
    )
    resource = FakeModel(
        id="ocid1.compartment.oc1..child",
        name="development",
        description="Development resources",
        freeform_tags={"environment": "development"},
        defined_tags={"Operations": {"CostCenter": "42"}},
    )

    assert instance.build_update_plan(resource) == {
        "update_needed": True,
        "update_model_fields": {
            "freeform_tags": {"environment": "production"},
            "defined_tags": {"Operations": {"CostCenter": "99"}},
            "name": "production",
            "description": "Production resources",
        },
        "strategy_operations": [],
    }


def test_create_resource_uses_identity_client_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_compartment")
    create_calls = []

    def create_compartment(create_compartment_details):
        create_calls.append(create_compartment_details)
        return FakeResponse(data=FakeModel(id="ocid1.compartment.oc1..child"))

    instance = make_compartment_module(
        module_obj,
        {
            "parent_compartment_id": "ocid1.compartment.oc1..parent",
            "name": "development",
            "description": "Development resources",
            "wait": True,
        },
        client=types.SimpleNamespace(create_compartment=create_compartment),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, target_states, **kwargs: FakeModel(
            id=resource_id,
            lifecycle_state="ACTIVE",
        ),
    )

    resource = instance.create_resource()

    assert create_calls[0].compartment_id == "ocid1.compartment.oc1..parent"
    assert create_calls[0].name == "development"
    assert resource.lifecycle_state == "ACTIVE"


def test_update_resource_uses_update_compartment_details_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_compartment")
    update_calls = []

    def update_compartment(compartment_id, update_compartment_details):
        update_calls.append((compartment_id, update_compartment_details))
        return FakeResponse(data=FakeModel(id=compartment_id))

    resource = FakeModel(
        id="ocid1.compartment.oc1..child",
        name="development",
        description="Development resources",
    )
    instance = make_compartment_module(
        module_obj,
        {"name": "production", "description": "Production resources", "wait": True},
        client=types.SimpleNamespace(update_compartment=update_compartment),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, target_states, **kwargs: FakeModel(
            id=resource_id,
            lifecycle_state="ACTIVE",
        ),
    )

    updated = instance.update_resource(resource)

    assert update_calls[0][0] == "ocid1.compartment.oc1..child"
    assert update_calls[0][1].name == "production"
    assert update_calls[0][1].description == "Production resources"
    assert updated.lifecycle_state == "ACTIVE"


def test_delete_resource_uses_delete_compartment_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_compartment")
    delete_calls = []

    def delete_compartment(compartment_id):
        delete_calls.append(compartment_id)
        return FakeResponse(data=None)

    instance = make_compartment_module(
        module_obj,
        {"wait": True},
        client=types.SimpleNamespace(delete_compartment=delete_compartment),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    monkeypatch.setattr(instance, "wait_for_resource_id", lambda *args, **kwargs: None)

    instance.delete_resource(FakeModel(id="ocid1.compartment.oc1..child"))

    assert delete_calls == ["ocid1.compartment.oc1..child"]


def test_create_requires_parent_name_and_description(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_compartment")
    instance = make_compartment_module(module_obj, {"name": "development"})

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.validate_create_request()

    assert "parent_compartment_id" in exc_info.value.payload["msg"]
    assert "description" in exc_info.value.payload["msg"]


def test_empty_description_is_valid_for_create(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_compartment")
    instance = make_compartment_module(
        module_obj,
        {
            "parent_compartment_id": "ocid1.compartment.oc1..parent",
            "name": "development",
            "description": "",
        },
    )

    instance.validate_create_request()
