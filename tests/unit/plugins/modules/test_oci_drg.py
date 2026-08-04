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


DRG_MODEL_NAMES = (
    "CreateDrgDetails",
    "UpdateDrgDetails",
)


def install_fake_oci(monkeypatch):
    return shared_install_fake_oci(
        monkeypatch,
        model_names=DRG_MODEL_NAMES,
    )


def make_drg_module(module_obj, params, client=None):
    return make_module_instance(
        module_obj,
        "OciDrgModule",
        params,
        client=client,
    )


def test_main_exposes_allow_duplicate_name_argument(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_drg")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured["argument_spec"] = kwargs["argument_spec"]
        return DummyModule({})

    class FakeDrgModule:
        def __init__(self, module):
            self.module = module

        def execute_resource_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciDrgModule", FakeDrgModule)

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
    assert "vcn_id" not in captured["argument_spec"]
    assert "display_name" not in captured["argument_spec"]


def test_build_create_drg_details_includes_supported_fields(monkeypatch):
    install_fake_oci(monkeypatch)

    drg_module = load_collection_module("oci_drg")
    details = drg_module.build_create_drg_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": "example-drg",
            "freeform_tags": {"env": "dev"},
            "defined_tags": {"Operations": {"CostCenter": "42"}},
        }
    )

    assert isinstance(details, FakeModel)
    assert details.compartment_id == "ocid1.compartment.oc1..example"
    assert details.display_name == "example-drg"
    assert details.freeform_tags == {"env": "dev"}
    assert details.defined_tags == {"Operations": {"CostCenter": "42"}}
    assert not hasattr(details, "vcn_id")


def test_build_update_plan_maps_drg_fields_to_update_model(monkeypatch):
    install_fake_oci(monkeypatch)

    drg_module = load_collection_module("oci_drg")
    instance = make_drg_module(
        drg_module,
        {"name": "updated-drg"},
    )
    resource = FakeModel(
        id="ocid1.drg.oc1..example",
        display_name="current-drg",
    )

    update_plan = instance.build_update_plan(resource)

    assert update_plan["update_needed"] is True
    assert update_plan["update_model_fields"] == {
        "display_name": "updated-drg",
    }
    assert update_plan["strategy_operations"] == []


def test_needs_update_returns_true_for_name_change(monkeypatch):
    install_fake_oci(monkeypatch)

    drg_module = load_collection_module("oci_drg")
    instance = make_drg_module(
        drg_module,
        {"name": "updated-drg"},
    )
    resource = FakeModel(
        id="ocid1.drg.oc1..example",
        display_name="current-drg",
    )

    assert instance.needs_update(resource) is True


def test_needs_update_returns_false_when_name_matches(monkeypatch):
    install_fake_oci(monkeypatch)

    drg_module = load_collection_module("oci_drg")
    instance = make_drg_module(
        drg_module,
        {"name": "current-drg"},
    )
    resource = FakeModel(
        id="ocid1.drg.oc1..example",
        display_name="current-drg",
    )

    assert instance.needs_update(resource) is False


def test_create_resource_uses_create_drg_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)

    drg_module = load_collection_module("oci_drg")
    create_calls = []
    response = FakeResponse(
        data=FakeModel(id="ocid1.drg.oc1..example"),
    )

    def create_drg(create_drg_details):
        create_calls.append(create_drg_details)
        return response

    instance = make_drg_module(
        drg_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "name": "example-drg",
            "wait": True,
        },
        client=types.SimpleNamespace(create_drg=create_drg),
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

    assert create_calls[0].compartment_id == "ocid1.compartment.oc1..example"
    assert create_calls[0].display_name == "example-drg"
    assert resource.id == "ocid1.drg.oc1..example"
    assert resource.lifecycle_state == "AVAILABLE"


def test_update_resource_uses_update_drg_details_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)

    drg_module = load_collection_module("oci_drg")
    update_calls = []
    response = FakeResponse(
        data=FakeModel(id="ocid1.drg.oc1..example"),
    )

    def update_drg(drg_id, update_drg_details):
        update_calls.append((drg_id, update_drg_details))
        return response

    resource = FakeModel(id="ocid1.drg.oc1..example")
    instance = make_drg_module(
        drg_module,
        {
            "name": "updated-drg",
            "freeform_tags": {"env": "prod"},
            "wait": True,
        },
        client=types.SimpleNamespace(update_drg=update_drg),
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

    assert update_calls[0][0] == "ocid1.drg.oc1..example"
    assert update_calls[0][1].display_name == "updated-drg"
    assert updated_resource.id == "ocid1.drg.oc1..example"


def test_delete_resource_uses_delete_drg_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)

    drg_module = load_collection_module("oci_drg")
    delete_calls = []
    response = FakeResponse(data=None)

    def delete_drg(drg_id):
        delete_calls.append(drg_id)
        return response

    resource = FakeModel(id="ocid1.drg.oc1..example")
    instance = make_drg_module(
        drg_module,
        {"wait": True},
        client=types.SimpleNamespace(delete_drg=delete_drg),
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

    assert delete_calls == ["ocid1.drg.oc1..example"]


def test_create_required_fields_enforced(monkeypatch):
    install_fake_oci(monkeypatch)

    drg_module = load_collection_module("oci_drg")
    instance = make_drg_module(
        drg_module,
        {"name": "example-drg"},
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.validate_create_request()

    assert "Creating a DRG requires" in exc_info.value.payload["msg"]
    assert "compartment_id" in exc_info.value.payload["msg"]
