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


BOOT_VOLUME_BACKUP_MODEL_NAMES = (
    "CreateBootVolumeBackupDetails",
    "UpdateBootVolumeBackupDetails",
    "RetentionDuration",
)

RETENTION_PERIOD_ARGUMENT_SPEC = {
    "type": "dict",
    "options": {
        "retention_time_amount": {"type": "int", "required": True},
        "retention_time_unit": {
            "type": "str",
            "choices": ["days", "years"],
            "required": True,
        },
    },
}


def install_fake_oci(monkeypatch):
    return shared_install_fake_oci(
        monkeypatch,
        model_names=BOOT_VOLUME_BACKUP_MODEL_NAMES,
    )


def make_boot_volume_backup_module(module_obj, params, client=None):
    return make_module_instance(
        module_obj,
        "OciBootVolumeBackupModule",
        params,
        client=client,
    )


def test_main_exposes_expected_arguments(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_boot_volume_backup")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured["argument_spec"] = kwargs["argument_spec"]
        return DummyModule({})

    class FakeBootVolumeBackupModule:
        def __init__(self, module):
            self.module = module

        def execute_resource_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(
        module_obj, "OciBootVolumeBackupModule", FakeBootVolumeBackupModule
    )

    module_obj.main()

    assert captured["run_called"] is True
    assert captured["argument_spec"]["boot_volume_backup_id"] == {"type": "str"}
    assert captured["argument_spec"]["boot_volume_id"] == {"type": "str"}
    assert captured["argument_spec"]["type"] == {
        "type": "str",
        "choices": ["full", "incremental"],
    }
    assert captured["argument_spec"]["kms_key_id"] == {"type": "str"}
    assert captured["argument_spec"]["name"] == {"type": "str"}
    assert captured["argument_spec"]["compartment_id"] == {"type": "str"}
    assert captured["argument_spec"]["allow_duplicate_name"] == {
        "type": "bool",
        "default": False,
    }
    assert captured["argument_spec"]["retention_period"] == RETENTION_PERIOD_ARGUMENT_SPEC
    assert captured["argument_spec"]["prevent_deletion_enabled"] == {"type": "bool"}
    assert captured["argument_spec"]["indefinite_retention_enabled"] == {
        "type": "bool"
    }
    assert captured["argument_spec"]["retention_lock_enabled"] == {"type": "bool"}
    assert "display_name" not in captured["argument_spec"]
    assert "is_prevent_deletion_enabled" not in captured["argument_spec"]
    assert "is_indefinite_retention_enabled" not in captured["argument_spec"]
    assert "is_retention_lock_enabled" not in captured["argument_spec"]


def test_build_create_boot_volume_backup_details_includes_supported_fields(monkeypatch):
    install_fake_oci(monkeypatch)

    backup_module = load_collection_module("oci_boot_volume_backup")
    details = backup_module.build_create_boot_volume_backup_details(
        {
            "boot_volume_id": "ocid1.bootvolume.oc1..example",
            "name": "example-boot-backup",
            "type": "full",
            "kms_key_id": "ocid1.key.oc1..example",
            "retention_period": {
                "retention_time_amount": 30,
                "retention_time_unit": "days",
            },
            "prevent_deletion_enabled": True,
            "indefinite_retention_enabled": False,
            "retention_lock_enabled": True,
            "freeform_tags": {"env": "dev"},
            "defined_tags": {"Operations": {"CostCenter": "42"}},
        }
    )

    assert isinstance(details, FakeModel)
    assert details.boot_volume_id == "ocid1.bootvolume.oc1..example"
    assert details.display_name == "example-boot-backup"
    # Ansible lowercase choice is normalized to the OCI wire constant.
    assert details.type == "FULL"
    assert details.kms_key_id == "ocid1.key.oc1..example"
    assert isinstance(details.retention_period, FakeModel)
    assert details.retention_period.retention_time_amount == 30
    assert details.retention_period.retention_time_unit == "DAYS"
    assert details.is_prevent_deletion_enabled is True
    assert details.is_indefinite_retention_enabled is False
    assert details.is_retention_lock_enabled is True
    assert details.freeform_tags == {"env": "dev"}
    assert details.defined_tags == {"Operations": {"CostCenter": "42"}}


def test_build_create_boot_volume_backup_details_omits_unset_optional_fields(monkeypatch):
    install_fake_oci(monkeypatch)

    backup_module = load_collection_module("oci_boot_volume_backup")
    details = backup_module.build_create_boot_volume_backup_details(
        {
            "boot_volume_id": "ocid1.bootvolume.oc1..example",
            "name": "example-boot-backup",
        }
    )

    assert not hasattr(details, "type")
    assert not hasattr(details, "kms_key_id")
    assert not hasattr(details, "retention_period")
    assert not hasattr(details, "is_prevent_deletion_enabled")
    assert not hasattr(details, "is_indefinite_retention_enabled")
    assert not hasattr(details, "is_retention_lock_enabled")
    assert not hasattr(details, "freeform_tags")


def test_build_update_plan_maps_backup_fields_to_update_model(monkeypatch):
    install_fake_oci(monkeypatch)

    backup_module = load_collection_module("oci_boot_volume_backup")
    instance = make_boot_volume_backup_module(
        backup_module,
        {"name": "updated-boot-backup"},
    )
    resource = FakeModel(
        id="ocid1.bootvolumebackup.oc1..example",
        display_name="current-boot-backup",
    )

    update_plan = instance.build_update_plan(resource)

    assert update_plan["update_needed"] is True
    assert update_plan["update_model_fields"] == {"display_name": "updated-boot-backup"}
    assert update_plan["strategy_operations"] == []


def test_build_update_plan_maps_retention_fields(monkeypatch):
    install_fake_oci(monkeypatch)

    backup_module = load_collection_module("oci_boot_volume_backup")
    instance = make_boot_volume_backup_module(
        backup_module,
        {
            "name": "current-boot-backup",
            "retention_period": {
                "retention_time_amount": 90,
                "retention_time_unit": "days",
            },
            "prevent_deletion_enabled": True,
            "indefinite_retention_enabled": True,
            "retention_lock_enabled": True,
        },
    )
    resource = FakeModel(
        id="ocid1.bootvolumebackup.oc1..example",
        display_name="current-boot-backup",
        retention_period=FakeModel(
            retention_time_amount=30,
            retention_time_unit="DAYS",
        ),
        is_prevent_deletion_enabled=False,
        is_indefinite_retention_enabled=False,
        is_retention_lock_enabled=False,
    )

    update_plan = instance.build_update_plan(resource)

    assert update_plan["update_needed"] is True
    assert update_plan["update_model_fields"]["retention_period"] == {
        "retention_time_amount": 90,
        "retention_time_unit": "days",
    }
    assert update_plan["update_model_fields"]["is_prevent_deletion_enabled"] is True
    assert update_plan["update_model_fields"]["is_indefinite_retention_enabled"] is True
    assert update_plan["update_model_fields"]["is_retention_lock_enabled"] is True


def test_needs_update_is_noop_when_retention_matches(monkeypatch):
    install_fake_oci(monkeypatch)

    backup_module = load_collection_module("oci_boot_volume_backup")
    instance = make_boot_volume_backup_module(
        backup_module,
        {
            "name": "current-boot-backup",
            "retention_period": {
                "retention_time_amount": 30,
                "retention_time_unit": "days",
            },
            "prevent_deletion_enabled": True,
            "indefinite_retention_enabled": False,
            "retention_lock_enabled": True,
        },
    )
    resource = FakeModel(
        id="ocid1.bootvolumebackup.oc1..example",
        display_name="current-boot-backup",
        retention_period=FakeModel(
            retention_time_amount=30,
            retention_time_unit="DAYS",
        ),
        is_prevent_deletion_enabled=True,
        is_indefinite_retention_enabled=False,
        is_retention_lock_enabled=True,
    )

    assert instance.needs_update(resource) is False


def test_build_update_details_wraps_retention_period(monkeypatch):
    install_fake_oci(monkeypatch)

    backup_module = load_collection_module("oci_boot_volume_backup")
    instance = make_boot_volume_backup_module(backup_module, {})

    details = instance.build_update_details(
        {
            "display_name": "updated-boot-backup",
            "retention_period": {
                "retention_time_amount": 1,
                "retention_time_unit": "years",
            },
            "is_prevent_deletion_enabled": True,
        }
    )

    assert details.display_name == "updated-boot-backup"
    assert isinstance(details.retention_period, FakeModel)
    assert details.retention_period.retention_time_amount == 1
    assert details.retention_period.retention_time_unit == "YEARS"
    assert details.is_prevent_deletion_enabled is True


def test_needs_update_ignores_create_only_type(monkeypatch):
    install_fake_oci(monkeypatch)

    backup_module = load_collection_module("oci_boot_volume_backup")
    # Rerunning the create task (which supplies type=full) against an existing
    # backup must be a no-op: type is create-only and its normalized wire value
    # must not trigger a spurious immutable-field failure or update.
    instance = make_boot_volume_backup_module(
        backup_module,
        {"name": "current-boot-backup", "type": "full"},
    )
    resource = FakeModel(
        id="ocid1.bootvolumebackup.oc1..example",
        display_name="current-boot-backup",
        type="FULL",
    )

    assert instance.needs_update(resource) is False


def test_needs_update_rejects_boot_volume_id_drift(monkeypatch):
    install_fake_oci(monkeypatch)

    backup_module = load_collection_module("oci_boot_volume_backup")
    instance = make_boot_volume_backup_module(
        backup_module,
        {"boot_volume_id": "ocid1.bootvolume.oc1..desired"},
    )
    resource = FakeModel(
        id="ocid1.bootvolumebackup.oc1..example",
        boot_volume_id="ocid1.bootvolume.oc1..current",
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "boot_volume_id" in exc_info.value.payload["msg"]


def test_needs_update_rejects_kms_key_id_drift(monkeypatch):
    install_fake_oci(monkeypatch)

    backup_module = load_collection_module("oci_boot_volume_backup")
    instance = make_boot_volume_backup_module(
        backup_module,
        {"kms_key_id": "ocid1.key.oc1..desired"},
    )
    resource = FakeModel(
        id="ocid1.bootvolumebackup.oc1..example",
        kms_key_id="ocid1.key.oc1..current",
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "kms_key_id" in exc_info.value.payload["msg"]


def test_needs_update_is_noop_when_create_only_ids_match(monkeypatch):
    install_fake_oci(monkeypatch)

    backup_module = load_collection_module("oci_boot_volume_backup")
    instance = make_boot_volume_backup_module(
        backup_module,
        {
            "name": "current-boot-backup",
            "boot_volume_id": "ocid1.bootvolume.oc1..example",
            "kms_key_id": "ocid1.key.oc1..example",
        },
    )
    resource = FakeModel(
        id="ocid1.bootvolumebackup.oc1..example",
        display_name="current-boot-backup",
        boot_volume_id="ocid1.bootvolume.oc1..example",
        kms_key_id="ocid1.key.oc1..example",
    )

    assert instance.needs_update(resource) is False


def test_create_resource_uses_create_boot_volume_backup_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)

    backup_module = load_collection_module("oci_boot_volume_backup")
    create_calls = []
    response = FakeResponse(data=FakeModel(id="ocid1.bootvolumebackup.oc1..example"))

    def create_boot_volume_backup(create_boot_volume_backup_details):
        create_calls.append(create_boot_volume_backup_details)
        return response

    instance = make_boot_volume_backup_module(
        backup_module,
        {
            "boot_volume_id": "ocid1.bootvolume.oc1..example",
            "name": "example-boot-backup",
            "type": "incremental",
            "wait": True,
        },
        client=types.SimpleNamespace(
            create_boot_volume_backup=create_boot_volume_backup
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

    resource = instance.create_resource()

    assert create_calls[0].boot_volume_id == "ocid1.bootvolume.oc1..example"
    assert create_calls[0].display_name == "example-boot-backup"
    assert create_calls[0].type == "INCREMENTAL"
    assert resource.id == "ocid1.bootvolumebackup.oc1..example"
    assert resource.lifecycle_state == "AVAILABLE"


def test_update_resource_uses_update_boot_volume_backup_details_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)

    backup_module = load_collection_module("oci_boot_volume_backup")
    update_calls = []
    response = FakeResponse(data=FakeModel(id="ocid1.bootvolumebackup.oc1..example"))

    def update_boot_volume_backup(boot_volume_backup_id, update_boot_volume_backup_details):
        update_calls.append(
            (boot_volume_backup_id, update_boot_volume_backup_details)
        )
        return response

    resource = FakeModel(id="ocid1.bootvolumebackup.oc1..example")
    instance = make_boot_volume_backup_module(
        backup_module,
        {
            "name": "updated-boot-backup",
            "freeform_tags": {"env": "prod"},
            "wait": True,
        },
        client=types.SimpleNamespace(
            update_boot_volume_backup=update_boot_volume_backup
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

    updated_resource = instance.update_resource(resource)

    assert update_calls[0][0] == "ocid1.bootvolumebackup.oc1..example"
    assert update_calls[0][1].display_name == "updated-boot-backup"
    assert updated_resource.id == "ocid1.bootvolumebackup.oc1..example"


def test_delete_resource_uses_delete_boot_volume_backup_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)

    backup_module = load_collection_module("oci_boot_volume_backup")
    delete_calls = []
    response = FakeResponse(data=None)

    def delete_boot_volume_backup(boot_volume_backup_id):
        delete_calls.append(boot_volume_backup_id)
        return response

    resource = FakeModel(id="ocid1.bootvolumebackup.oc1..example")
    instance = make_boot_volume_backup_module(
        backup_module,
        {"wait": True},
        client=types.SimpleNamespace(
            delete_boot_volume_backup=delete_boot_volume_backup
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

    assert delete_calls == ["ocid1.bootvolumebackup.oc1..example"]


def test_create_required_fields_enforced(monkeypatch):
    install_fake_oci(monkeypatch)

    backup_module = load_collection_module("oci_boot_volume_backup")
    instance = make_boot_volume_backup_module(
        backup_module,
        {"name": "example-boot-backup"},
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.validate_create_request()

    assert "Creating a boot volume backup requires" in exc_info.value.payload["msg"]
    assert "boot_volume_id" in exc_info.value.payload["msg"]


def test_name_lookup_requires_compartment_id(monkeypatch):
    install_fake_oci(monkeypatch)

    backup_module = load_collection_module("oci_boot_volume_backup")
    instance = make_boot_volume_backup_module(
        backup_module,
        {
            "name": "example-boot-backup",
            "boot_volume_id": "ocid1.bootvolume.oc1..example",
        },
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.validate_name_lookup_scope()

    assert (
        "Using name lookup for boot volume backup requires"
        in exc_info.value.payload["msg"]
    )
    assert "compartment_id" in exc_info.value.payload["msg"]


def test_name_lookup_requires_boot_volume_id(monkeypatch):
    install_fake_oci(monkeypatch)

    backup_module = load_collection_module("oci_boot_volume_backup")
    instance = make_boot_volume_backup_module(
        backup_module,
        {
            "name": "example-boot-backup",
            "compartment_id": "ocid1.compartment.oc1..example",
        },
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.validate_name_lookup_scope()

    assert (
        "Using name lookup for boot volume backup requires"
        in exc_info.value.payload["msg"]
    )
    assert "boot_volume_id" in exc_info.value.payload["msg"]
