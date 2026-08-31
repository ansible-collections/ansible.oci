from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import pytest

from conftest import (
    DummyModule,
    ExitJsonCalled,
    FakeModel,
    FakeResponse,
    install_fake_oci,
    load_collection_module,
    make_module_instance,
    raising,
)


def make_volume_group_backup_info_module(module_obj, params, client=None):
    return make_module_instance(
        module_obj,
        "OciVolumeGroupBackupInfoModule",
        params,
        client=client,
    )


def test_main_requires_compartment_id_or_backup_id(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_volume_group_backup_info")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured["required_one_of"] = kwargs["required_one_of"]
        return DummyModule({})

    class FakeInfoModule:
        def __init__(self, module):
            self.module = module

        def execute_info_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(
        module_obj, "OciVolumeGroupBackupInfoModule", FakeInfoModule
    )

    module_obj.main()

    assert captured["run_called"] is True
    assert captured["required_one_of"] == [
        ["compartment_id", "volume_group_backup_id"]
    ]


def test_fetch_resources_prefers_id_lookup(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_volume_group_backup_info")
    get_calls = []

    def get_volume_group_backup(**kwargs):
        get_calls.append(kwargs)
        return FakeResponse(
            data=FakeModel(
                id=kwargs["volume_group_backup_id"],
                display_name="example-group-backup",
            )
        )

    instance = make_volume_group_backup_info_module(
        info_module,
        {"volume_group_backup_id": "ocid1.volumegroupbackup.oc1..example"},
        client=types.SimpleNamespace(
            get_volume_group_backup=get_volume_group_backup
        ),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        raising(AssertionError("list_all_resources should not be called")),
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )

    resources = instance.fetch_resources()

    assert len(resources) == 1
    assert resources[0].id == "ocid1.volumegroupbackup.oc1..example"
    assert get_calls == [
        {"volume_group_backup_id": "ocid1.volumegroupbackup.oc1..example"}
    ]


def test_fetch_resources_lists_by_supported_filters(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_volume_group_backup_info")
    paginate_calls = []
    instance = make_volume_group_backup_info_module(
        info_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "volume_group_id": "ocid1.volumegroup.oc1..example",
        },
        client=types.SimpleNamespace(list_volume_group_backups="list_method"),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda list_fn, **kwargs: paginate_calls.append((list_fn, kwargs)) or [],
    )

    resources = instance.fetch_resources()

    assert resources == []
    assert paginate_calls == [
        (
            "list_method",
            {
                "compartment_id": "ocid1.compartment.oc1..example",
                "volume_group_id": "ocid1.volumegroup.oc1..example",
            },
        )
    ]


def test_fetch_resources_does_not_send_lifecycle_state_as_a_list_filter(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_volume_group_backup_info")
    paginate_calls = []
    instance = make_volume_group_backup_info_module(
        info_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "lifecycle_state": "AVAILABLE",
        },
        client=types.SimpleNamespace(list_volume_group_backups="list_method"),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda list_fn, **kwargs: paginate_calls.append((list_fn, kwargs)) or [],
    )

    instance.fetch_resources()

    assert paginate_calls == [
        ("list_method", {"compartment_id": "ocid1.compartment.oc1..example"})
    ]


def test_fetch_resources_filters_list_results_by_lifecycle_state_locally(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_volume_group_backup_info")
    available_backup = FakeModel(
        id="ocid1.volumegroupbackup.oc1..available",
        display_name="available-group-backup",
        lifecycle_state="AVAILABLE",
    )
    terminated_backup = FakeModel(
        id="ocid1.volumegroupbackup.oc1..terminated",
        display_name="terminated-group-backup",
        lifecycle_state="TERMINATED",
    )
    instance = make_volume_group_backup_info_module(
        info_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "lifecycle_state": "AVAILABLE",
        },
        client=types.SimpleNamespace(list_volume_group_backups="list_method"),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda list_fn, **kwargs: [terminated_backup, available_backup],
    )

    resources = instance.fetch_resources()

    assert resources == [available_backup]


def test_fetch_resources_filters_id_lookup_result_by_lifecycle_state(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_volume_group_backup_info")
    instance = make_volume_group_backup_info_module(
        info_module,
        {
            "volume_group_backup_id": "ocid1.volumegroupbackup.oc1..example",
            "lifecycle_state": "AVAILABLE",
        },
        client=types.SimpleNamespace(
            get_volume_group_backup=lambda **kwargs: FakeResponse(
                data=FakeModel(
                    id=kwargs["volume_group_backup_id"],
                    display_name="example-group-backup",
                    lifecycle_state="TERMINATED",
                )
            )
        ),
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )

    assert instance.fetch_resources() == []


def test_run_returns_volume_group_backups_key(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_volume_group_backup_info")
    resource = FakeModel(
        id="ocid1.volumegroupbackup.oc1..example",
        display_name="example-group-backup",
        lifecycle_state="AVAILABLE",
    )
    instance = make_volume_group_backup_info_module(
        info_module,
        {"compartment_id": "ocid1.compartment.oc1..example"},
    )
    monkeypatch.setattr(instance, "fetch_resources", lambda: [resource])

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_info_module()

    assert exc_info.value.payload == {
        "changed": False,
        "volume_group_backups": [
            {
                "id": "ocid1.volumegroupbackup.oc1..example",
                "name": "example-group-backup",
                "lifecycle_state": "AVAILABLE",
            }
        ],
    }
