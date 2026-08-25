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


VOLUME_GROUP_MODEL_NAMES = (
    "CreateVolumeGroupDetails",
    "UpdateVolumeGroupDetails",
    "VolumeGroupSourceFromVolumesDetails",
)


def install_fake_oci(monkeypatch):
    return shared_install_fake_oci(
        monkeypatch,
        model_names=VOLUME_GROUP_MODEL_NAMES,
    )


def make_volume_group_module(module_obj, params, client=None):
    return make_module_instance(
        module_obj,
        "OciVolumeGroupModule",
        params,
        client=client,
    )


def test_main_exposes_expected_arguments(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_group")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured["argument_spec"] = kwargs["argument_spec"]
        return DummyModule({})

    class FakeVolumeGroupModule:
        def __init__(self, module):
            self.module = module

        def execute_resource_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciVolumeGroupModule", FakeVolumeGroupModule)

    module_obj.main()

    assert captured["run_called"] is True
    assert captured["argument_spec"]["volume_group_id"] == {"type": "str"}
    assert captured["argument_spec"]["availability_domain"] == {"type": "str"}
    assert captured["argument_spec"]["volume_ids"] == {
        "type": "list",
        "elements": "str",
    }
    assert captured["argument_spec"]["backup_policy_id"] == {"type": "str"}
    assert captured["argument_spec"]["name"] == {"type": "str"}
    assert "display_name" not in captured["argument_spec"]


def test_build_create_volume_group_details_wraps_volume_ids_in_source_details(monkeypatch):
    install_fake_oci(monkeypatch)

    group_module = load_collection_module("oci_volume_group")
    details = group_module.build_create_volume_group_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "availability_domain": "Uocm:PHX-AD-1",
            "name": "example-group",
            "volume_ids": ["ocid1.volume.oc1..a", "ocid1.volume.oc1..b"],
            "freeform_tags": {"env": "dev"},
            "defined_tags": {"Operations": {"CostCenter": "42"}},
        }
    )

    assert isinstance(details, FakeModel)
    assert details.compartment_id == "ocid1.compartment.oc1..example"
    assert details.availability_domain == "Uocm:PHX-AD-1"
    assert details.display_name == "example-group"
    # Member volumes are supplied through a source-details model on create.
    assert isinstance(details.source_details, FakeModel)
    assert details.source_details.volume_ids == [
        "ocid1.volume.oc1..a",
        "ocid1.volume.oc1..b",
    ]
    assert details.freeform_tags == {"env": "dev"}
    assert not hasattr(details, "backup_policy_id")


def test_build_update_plan_maps_group_fields_to_update_model(monkeypatch):
    install_fake_oci(monkeypatch)

    group_module = load_collection_module("oci_volume_group")
    instance = make_volume_group_module(
        group_module,
        {
            "name": "updated-group",
            "volume_ids": ["ocid1.volume.oc1..a", "ocid1.volume.oc1..c"],
        },
    )
    resource = FakeModel(
        id="ocid1.volumegroup.oc1..example",
        display_name="current-group",
        availability_domain="Uocm:PHX-AD-1",
        compartment_id="ocid1.compartment.oc1..example",
        volume_ids=["ocid1.volume.oc1..a", "ocid1.volume.oc1..b"],
    )

    update_plan = instance.build_update_plan(resource)

    assert update_plan["update_needed"] is True
    assert update_plan["update_model_fields"] == {
        "display_name": "updated-group",
        "volume_ids": ["ocid1.volume.oc1..a", "ocid1.volume.oc1..c"],
    }


def test_needs_update_false_when_volume_ids_only_reordered(monkeypatch):
    install_fake_oci(monkeypatch)

    group_module = load_collection_module("oci_volume_group")
    # volume_ids compares as an order-insensitive set, so reordering the same
    # members must not be reported as drift.
    instance = make_volume_group_module(
        group_module,
        {
            "name": "current-group",
            "availability_domain": "Uocm:PHX-AD-1",
            "compartment_id": "ocid1.compartment.oc1..example",
            "volume_ids": ["ocid1.volume.oc1..b", "ocid1.volume.oc1..a"],
        },
    )
    resource = FakeModel(
        id="ocid1.volumegroup.oc1..example",
        display_name="current-group",
        availability_domain="Uocm:PHX-AD-1",
        compartment_id="ocid1.compartment.oc1..example",
        volume_ids=["ocid1.volume.oc1..a", "ocid1.volume.oc1..b"],
    )

    assert instance.needs_update(resource) is False


def test_needs_update_true_when_volume_ids_change(monkeypatch):
    install_fake_oci(monkeypatch)

    group_module = load_collection_module("oci_volume_group")
    instance = make_volume_group_module(
        group_module,
        {"volume_ids": ["ocid1.volume.oc1..a", "ocid1.volume.oc1..c"]},
    )
    resource = FakeModel(
        id="ocid1.volumegroup.oc1..example",
        display_name="current-group",
        volume_ids=["ocid1.volume.oc1..a", "ocid1.volume.oc1..b"],
    )

    assert instance.needs_update(resource) is True


def test_changing_availability_domain_fails_as_immutable(monkeypatch):
    install_fake_oci(monkeypatch)

    group_module = load_collection_module("oci_volume_group")
    instance = make_volume_group_module(
        group_module,
        {"availability_domain": "Uocm:PHX-AD-2"},
    )
    resource = FakeModel(
        id="ocid1.volumegroup.oc1..example",
        display_name="current-group",
        availability_domain="Uocm:PHX-AD-1",
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "availability_domain" in exc_info.value.payload["msg"]


def test_create_resource_uses_create_volume_group_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)

    group_module = load_collection_module("oci_volume_group")
    create_calls = []
    response = FakeResponse(data=FakeModel(id="ocid1.volumegroup.oc1..example"))

    def create_volume_group(create_volume_group_details):
        create_calls.append(create_volume_group_details)
        return response

    instance = make_volume_group_module(
        group_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "availability_domain": "Uocm:PHX-AD-1",
            "name": "example-group",
            "volume_ids": ["ocid1.volume.oc1..a"],
            "wait": True,
        },
        client=types.SimpleNamespace(create_volume_group=create_volume_group),
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

    assert create_calls[0].display_name == "example-group"
    assert create_calls[0].source_details.volume_ids == ["ocid1.volume.oc1..a"]
    assert resource.id == "ocid1.volumegroup.oc1..example"
    assert resource.lifecycle_state == "AVAILABLE"


def test_update_resource_uses_update_volume_group_details_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)

    group_module = load_collection_module("oci_volume_group")
    update_calls = []
    response = FakeResponse(data=FakeModel(id="ocid1.volumegroup.oc1..example"))

    def update_volume_group(volume_group_id, update_volume_group_details):
        update_calls.append((volume_group_id, update_volume_group_details))
        return response

    resource = FakeModel(
        id="ocid1.volumegroup.oc1..example",
        display_name="current-group",
        volume_ids=["ocid1.volume.oc1..a"],
    )
    instance = make_volume_group_module(
        group_module,
        {
            "volume_ids": ["ocid1.volume.oc1..a", "ocid1.volume.oc1..b"],
            "wait": True,
        },
        client=types.SimpleNamespace(update_volume_group=update_volume_group),
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

    assert update_calls[0][0] == "ocid1.volumegroup.oc1..example"
    assert update_calls[0][1].volume_ids == [
        "ocid1.volume.oc1..a",
        "ocid1.volume.oc1..b",
    ]
    assert updated_resource.id == "ocid1.volumegroup.oc1..example"


def test_delete_resource_uses_delete_volume_group_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)

    group_module = load_collection_module("oci_volume_group")
    delete_calls = []
    response = FakeResponse(data=None)

    def delete_volume_group(volume_group_id):
        delete_calls.append(volume_group_id)
        return response

    resource = FakeModel(id="ocid1.volumegroup.oc1..example")
    instance = make_volume_group_module(
        group_module,
        {"wait": True},
        client=types.SimpleNamespace(delete_volume_group=delete_volume_group),
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

    assert delete_calls == ["ocid1.volumegroup.oc1..example"]


def test_create_required_fields_enforced(monkeypatch):
    install_fake_oci(monkeypatch)

    group_module = load_collection_module("oci_volume_group")
    instance = make_volume_group_module(
        group_module,
        {"name": "example-group"},
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.validate_create_request()

    assert "Creating a volume group requires" in exc_info.value.payload["msg"]
    assert "availability_domain" in exc_info.value.payload["msg"]
    assert "volume_ids" in exc_info.value.payload["msg"]
