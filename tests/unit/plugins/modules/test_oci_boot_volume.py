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
    raising,
)


BOOT_VOLUME_MODEL_NAMES = (
    "CreateBootVolumeDetails",
    "UpdateBootVolumeDetails",
    "BootVolumeSourceFromBootVolumeBackupDetails",
)

SOURCE_DETAILS_ARGUMENT_SPEC = {
    "type": "dict",
    "options": {
        "type": {
            "type": "str",
            "required": True,
            "choices": ["bootVolumeBackup"],
        },
        "id": {"type": "str", "required": True},
    },
}


def _fake_source_model(source_type):
    class FakeSourceModel(FakeModel):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            if "type" not in kwargs:
                self.type = source_type

    return FakeSourceModel


def install_fake_oci(monkeypatch):
    oci_module, service_error = shared_install_fake_oci(
        monkeypatch,
        model_names=BOOT_VOLUME_MODEL_NAMES,
    )
    oci_module.core.models.BootVolumeSourceFromBootVolumeBackupDetails = (
        _fake_source_model("bootVolumeBackup")
    )
    return oci_module, service_error


def make_boot_volume_module(module_obj, params, client=None):
    return make_module_instance(
        module_obj,
        "OciBootVolumeModule",
        params,
        client=client,
    )


def test_main_exposes_expected_arguments(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_boot_volume")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured["argument_spec"] = kwargs["argument_spec"]
        return DummyModule({})

    class FakeBootVolumeModule:
        def __init__(self, module):
            self.module = module

        def execute_resource_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciBootVolumeModule", FakeBootVolumeModule)

    module_obj.main()

    assert captured["run_called"] is True
    assert captured["argument_spec"]["boot_volume_id"] == {"type": "str"}
    assert captured["argument_spec"]["availability_domain"] == {"type": "str"}
    assert captured["argument_spec"]["size_in_gbs"] == {"type": "int"}
    assert captured["argument_spec"]["vpus_per_gb"] == {"type": "int"}
    assert captured["argument_spec"]["source_details"] == SOURCE_DETAILS_ARGUMENT_SPEC
    assert captured["argument_spec"]["name"] == {"type": "str"}
    assert "display_name" not in captured["argument_spec"]
    assert "kms_key_id" not in captured["argument_spec"]
    assert "backup_policy_id" not in captured["argument_spec"]
    assert "cluster_placement_group_id" not in captured["argument_spec"]
    assert "reservations_enabled" not in captured["argument_spec"]
    assert "performance_based_auto_tune" not in captured["argument_spec"]
    assert "autotune_policies" not in captured["argument_spec"]
    assert "boot_volume_replicas" not in captured["argument_spec"]


def test_build_source_details_from_backup(monkeypatch):
    install_fake_oci(monkeypatch)

    boot_volume_module = load_collection_module("oci_boot_volume")
    details = boot_volume_module.build_source_details(
        {"type": "bootVolumeBackup", "id": "ocid1.bootvolumebackup.oc1..example"}
    )

    assert isinstance(details, FakeModel)
    assert details.type == "bootVolumeBackup"
    assert details.id == "ocid1.bootvolumebackup.oc1..example"


def test_build_source_details_omits_unset_source(monkeypatch):
    install_fake_oci(monkeypatch)

    boot_volume_module = load_collection_module("oci_boot_volume")
    assert boot_volume_module.build_source_details(None) is None
    assert boot_volume_module.build_source_details({}) is None


def test_build_source_details_rejects_unknown_type(monkeypatch):
    install_fake_oci(monkeypatch)

    boot_volume_module = load_collection_module("oci_boot_volume")
    with pytest.raises(ValueError, match="bootVolumeBackup"):
        boot_volume_module.build_source_details(
            {"type": "bootVolume", "id": "ocid1.bootvolume.oc1..example"}
        )


def test_build_create_boot_volume_details_includes_source_details_from_backup(
    monkeypatch,
):
    install_fake_oci(monkeypatch)

    boot_volume_module = load_collection_module("oci_boot_volume")
    details = boot_volume_module.build_create_boot_volume_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "availability_domain": "Uocm:PHX-AD-1",
            "name": "restored-boot-volume",
            "source_details": {
                "type": "bootVolumeBackup",
                "id": "ocid1.bootvolumebackup.oc1..example",
            },
            "freeform_tags": {"env": "dev"},
        }
    )

    assert isinstance(details, FakeModel)
    assert details.compartment_id == "ocid1.compartment.oc1..example"
    assert details.availability_domain == "Uocm:PHX-AD-1"
    assert details.display_name == "restored-boot-volume"
    assert isinstance(details.source_details, FakeModel)
    assert details.source_details.type == "bootVolumeBackup"
    assert details.source_details.id == "ocid1.bootvolumebackup.oc1..example"
    assert details.freeform_tags == {"env": "dev"}
    assert not hasattr(details, "size_in_gbs")
    assert not hasattr(details, "vpus_per_gb")


def test_build_create_boot_volume_details_includes_optional_size_and_vpus(monkeypatch):
    install_fake_oci(monkeypatch)

    boot_volume_module = load_collection_module("oci_boot_volume")
    details = boot_volume_module.build_create_boot_volume_details(
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "availability_domain": "Uocm:PHX-AD-1",
            "name": "restored-boot-volume",
            "size_in_gbs": 100,
            "vpus_per_gb": 20,
            "source_details": {
                "type": "bootVolumeBackup",
                "id": "ocid1.bootvolumebackup.oc1..example",
            },
        }
    )

    assert details.size_in_gbs == 100
    assert details.vpus_per_gb == 20


def test_needs_update_is_noop_when_source_details_match(monkeypatch):
    install_fake_oci(monkeypatch)

    boot_volume_module = load_collection_module("oci_boot_volume")
    instance = make_boot_volume_module(
        boot_volume_module,
        {
            "name": "restored-boot-volume",
            "source_details": {
                "type": "bootVolumeBackup",
                "id": "ocid1.bootvolumebackup.oc1..example",
            },
        },
    )
    resource = FakeModel(
        id="ocid1.bootvolume.oc1..example",
        display_name="restored-boot-volume",
        source_details=FakeModel(
            type="bootVolumeBackup",
            id="ocid1.bootvolumebackup.oc1..example",
        ),
    )

    assert instance.needs_update(resource) is False


def test_needs_update_rejects_source_details_drift(monkeypatch):
    install_fake_oci(monkeypatch)

    boot_volume_module = load_collection_module("oci_boot_volume")
    instance = make_boot_volume_module(
        boot_volume_module,
        {
            "source_details": {
                "type": "bootVolumeBackup",
                "id": "ocid1.bootvolumebackup.oc1..desired",
            },
        },
    )
    resource = FakeModel(
        id="ocid1.bootvolume.oc1..example",
        source_details=FakeModel(
            type="bootVolumeBackup",
            id="ocid1.bootvolumebackup.oc1..current",
        ),
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.needs_update(resource)

    assert "source_details" in exc_info.value.payload["msg"]


def test_needs_update_skips_source_details_when_omitted(monkeypatch):
    install_fake_oci(monkeypatch)

    boot_volume_module = load_collection_module("oci_boot_volume")
    instance = make_boot_volume_module(
        boot_volume_module,
        {"name": "current-boot-volume"},
    )
    resource = FakeModel(
        id="ocid1.bootvolume.oc1..example",
        display_name="current-boot-volume",
        source_details=FakeModel(
            type="bootVolumeBackup",
            id="ocid1.bootvolumebackup.oc1..example",
        ),
    )

    assert instance.needs_update(resource) is False


def test_create_required_fields_enforced(monkeypatch):
    install_fake_oci(monkeypatch)

    boot_volume_module = load_collection_module("oci_boot_volume")
    instance = make_boot_volume_module(
        boot_volume_module,
        {"name": "restored-boot-volume"},
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.validate_create_request()

    assert "Creating a boot volume requires" in exc_info.value.payload["msg"]
    assert "availability_domain" in exc_info.value.payload["msg"]
    assert "source_details" in exc_info.value.payload["msg"]


def test_create_resource_passes_source_details_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)

    boot_volume_module = load_collection_module("oci_boot_volume")
    create_calls = []
    response = FakeResponse(data=FakeModel(id="ocid1.bootvolume.oc1..restored"))

    def create_boot_volume(create_boot_volume_details):
        create_calls.append(create_boot_volume_details)
        return response

    instance = make_boot_volume_module(
        boot_volume_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "availability_domain": "Uocm:PHX-AD-1",
            "name": "restored-boot-volume",
            "source_details": {
                "type": "bootVolumeBackup",
                "id": "ocid1.bootvolumebackup.oc1..example",
            },
            "wait": True,
        },
        client=types.SimpleNamespace(create_boot_volume=create_boot_volume),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, target_states, **kwargs: FakeModel(
            id=resource_id,
            lifecycle_state="AVAILABLE",
            is_hydrated=True,
            source_details=FakeModel(
                type="bootVolumeBackup",
                id="ocid1.bootvolumebackup.oc1..example",
            ),
        ),
    )

    resource = instance.create_resource()

    assert create_calls[0].source_details.type == "bootVolumeBackup"
    assert create_calls[0].source_details.id == "ocid1.bootvolumebackup.oc1..example"
    assert resource.id == "ocid1.bootvolume.oc1..restored"
    assert resource.lifecycle_state == "AVAILABLE"
    assert resource.is_hydrated is True


def test_wait_for_resource_id_waits_until_hydrated_after_available(monkeypatch):
    install_fake_oci(monkeypatch)

    boot_volume_module = load_collection_module("oci_boot_volume")
    hydrating = FakeModel(
        id="ocid1.bootvolume.oc1..example",
        lifecycle_state="AVAILABLE",
        is_hydrated=False,
    )
    ready = FakeModel(
        id="ocid1.bootvolume.oc1..example",
        lifecycle_state="AVAILABLE",
        is_hydrated=True,
    )
    wait_until_kwargs = {}

    def fake_base_wait(self, resource_id, target_states, failure_states=None):
        return hydrating

    def fake_wait_until(client, response, **kwargs):
        wait_until_kwargs.update(kwargs)
        return FakeResponse(data=ready)

    monkeypatch.setattr(
        boot_volume_module.OciResourceBase,
        "wait_for_resource_id",
        fake_base_wait,
    )
    monkeypatch.setattr(
        boot_volume_module.oci, "wait_until", fake_wait_until, raising=False
    )

    instance = make_boot_volume_module(
        boot_volume_module,
        {"wait": True, "wait_timeout": 90, "wait_interval": 5},
    )
    monkeypatch.setattr(
        instance,
        "get_resource_response",
        lambda resource_id: FakeResponse(data=hydrating),
    )

    resource = instance.wait_for_resource_id(
        "ocid1.bootvolume.oc1..example",
        boot_volume_module.WAIT_FOR_BOOT_VOLUME_STATES,
    )

    evaluate = wait_until_kwargs["evaluate_response"]
    assert resource.is_hydrated is True
    assert wait_until_kwargs["max_wait_seconds"] == 90
    assert wait_until_kwargs["max_interval_seconds"] == 5
    assert evaluate(FakeResponse(data=hydrating)) is False
    assert evaluate(FakeResponse(data=ready)) is True


def test_wait_for_resource_id_skips_hydration_wait_when_already_hydrated(monkeypatch):
    install_fake_oci(monkeypatch)

    boot_volume_module = load_collection_module("oci_boot_volume")
    ready = FakeModel(
        id="ocid1.bootvolume.oc1..example",
        lifecycle_state="AVAILABLE",
        is_hydrated=True,
    )

    monkeypatch.setattr(
        boot_volume_module.OciResourceBase,
        "wait_for_resource_id",
        lambda self, resource_id, target_states, failure_states=None: ready,
    )
    monkeypatch.setattr(
        boot_volume_module.oci,
        "wait_until",
        raising(AssertionError("hydration wait should not run")),
        raising=False,
    )

    instance = make_boot_volume_module(boot_volume_module, {"wait": True})
    resource = instance.wait_for_resource_id(
        "ocid1.bootvolume.oc1..example",
        boot_volume_module.WAIT_FOR_BOOT_VOLUME_STATES,
    )

    assert resource is ready


def test_wait_for_resource_id_skips_hydration_wait_when_wait_disabled(monkeypatch):
    install_fake_oci(monkeypatch)

    boot_volume_module = load_collection_module("oci_boot_volume")
    hydrating = FakeModel(
        id="ocid1.bootvolume.oc1..example",
        lifecycle_state="AVAILABLE",
        is_hydrated=False,
    )

    monkeypatch.setattr(
        boot_volume_module.OciResourceBase,
        "wait_for_resource_id",
        lambda self, resource_id, target_states, failure_states=None: hydrating,
    )
    monkeypatch.setattr(
        boot_volume_module.oci,
        "wait_until",
        raising(AssertionError("hydration wait should not run")),
        raising=False,
    )

    instance = make_boot_volume_module(boot_volume_module, {"wait": False})
    resource = instance.wait_for_resource_id(
        "ocid1.bootvolume.oc1..example",
        boot_volume_module.WAIT_FOR_BOOT_VOLUME_STATES,
    )

    assert resource is hydrating


def test_update_resource_waits_for_hydration_before_mutating(monkeypatch):
    install_fake_oci(monkeypatch)

    boot_volume_module = load_collection_module("oci_boot_volume")
    hydrating = FakeModel(
        id="ocid1.bootvolume.oc1..example",
        display_name="restored-boot-volume",
        is_hydrated=False,
    )
    ready = FakeModel(
        id="ocid1.bootvolume.oc1..example",
        display_name="restored-boot-volume",
        is_hydrated=True,
    )
    call_order = []
    update_calls = []

    def fake_wait_until(client, response, **kwargs):
        call_order.append("hydrate")
        return FakeResponse(data=ready)

    def update_boot_volume(boot_volume_id, update_boot_volume_details):
        call_order.append("update")
        update_calls.append((boot_volume_id, update_boot_volume_details))
        return FakeResponse(data=FakeModel(id=boot_volume_id))

    instance = make_boot_volume_module(
        boot_volume_module,
        {
            "name": "updated-boot-volume",
            "vpus_per_gb": 20,
            "wait": True,
            "wait_timeout": 90,
            "wait_interval": 5,
        },
        client=types.SimpleNamespace(update_boot_volume=update_boot_volume),
    )
    monkeypatch.setattr(
        boot_volume_module.oci, "wait_until", fake_wait_until, raising=False
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    monkeypatch.setattr(
        instance,
        "get_resource_response",
        lambda resource_id: FakeResponse(data=hydrating),
    )
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, target_states, **kwargs: FakeModel(
            id=resource_id,
            lifecycle_state="AVAILABLE",
            is_hydrated=True,
        ),
    )

    updated_resource = instance.update_resource(hydrating)

    assert call_order == ["hydrate", "update"]
    assert update_calls[0][0] == "ocid1.bootvolume.oc1..example"
    assert update_calls[0][1].display_name == "updated-boot-volume"
    assert update_calls[0][1].vpus_per_gb == 20
    assert updated_resource.lifecycle_state == "AVAILABLE"


def test_delete_resource_uses_delete_boot_volume_and_waits(monkeypatch):
    install_fake_oci(monkeypatch)

    boot_volume_module = load_collection_module("oci_boot_volume")
    delete_calls = []
    response = FakeResponse(data=None)

    def delete_boot_volume(boot_volume_id):
        delete_calls.append(boot_volume_id)
        return response

    resource = FakeModel(id="ocid1.bootvolume.oc1..example")
    instance = make_boot_volume_module(
        boot_volume_module,
        {"wait": True},
        client=types.SimpleNamespace(delete_boot_volume=delete_boot_volume),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    monkeypatch.setattr(
        instance,
        "wait_for_resource_id",
        lambda resource_id, target_states, **kwargs: None,
    )

    instance.delete_resource(resource)

    assert delete_calls == ["ocid1.bootvolume.oc1..example"]
