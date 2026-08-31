from __future__ import absolute_import, division, print_function
__metaclass__ = type

from conftest import load_collection_module


def test_build_backup_update_field_specs_inserts_source_identity_field():
    oci_backup = load_collection_module("oci_backup")

    specs = oci_backup.build_backup_update_field_specs("boot_volume_id")
    param_names = [spec["param_name"] for spec in specs]

    assert param_names == [
        "name",
        "retention_period",
        "prevent_deletion_enabled",
        "indefinite_retention_enabled",
        "retention_lock_enabled",
        "boot_volume_id",
        "kms_key_id",
    ]
    assert specs[5]["resource_field"] == "boot_volume_id"
    assert specs[5]["is_mutable"] is False
    assert specs[6]["immutable_reason"] == (
        "changing a backup's encryption key after create is not "
        "supported"
    )

    volume_specs = oci_backup.build_backup_update_field_specs("volume_id")
    assert volume_specs[5]["param_name"] == "volume_id"
    assert [
        spec["param_name"]
        for spec in specs
        if spec["param_name"] != "boot_volume_id"
    ] == [
        spec["param_name"]
        for spec in volume_specs
        if spec["param_name"] != "volume_id"
    ]


def test_build_backup_update_field_specs_exclude_and_extra_immutable():
    oci_backup = load_collection_module("oci_backup")

    specs = oci_backup.build_backup_update_field_specs(
        "volume_group_id",
        exclude=("kms_key_id",),
        extra_immutable=("compartment_id",),
    )
    param_names = [spec["param_name"] for spec in specs]

    assert param_names == [
        "name",
        "retention_period",
        "prevent_deletion_enabled",
        "indefinite_retention_enabled",
        "retention_lock_enabled",
        "volume_group_id",
        "compartment_id",
    ]
    assert specs[-1] == {
        "param_name": "compartment_id",
        "resource_field": "compartment_id",
        "is_mutable": False,
    }
