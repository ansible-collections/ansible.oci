"""Shared helpers for OCI volume and boot-volume backup modules."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type


def build_backup_update_field_specs(source_id_param):
    """Return update-planner specs shared by volume and boot-volume backups.

    ``source_id_param`` is the create-only source identity field
    (``volume_id`` or ``boot_volume_id``). Name, retention flags, and
    ``kms_key_id`` are identical across both backup APIs.
    """
    return [
        {
            "param_name": "name",
            "resource_field": "display_name",
            "update_field": "display_name",
            "is_mutable": True,
        },
        {
            "param_name": "retention_period",
            "resource_field": "retention_period",
            "update_field": "retention_period",
            "is_mutable": True,
            "compare": "subset_dict",
        },
        {
            "param_name": "prevent_deletion_enabled",
            "resource_field": "is_prevent_deletion_enabled",
            "update_field": "is_prevent_deletion_enabled",
            "is_mutable": True,
        },
        {
            "param_name": "indefinite_retention_enabled",
            "resource_field": "is_indefinite_retention_enabled",
            "update_field": "is_indefinite_retention_enabled",
            "is_mutable": True,
        },
        {
            "param_name": "retention_lock_enabled",
            "resource_field": "is_retention_lock_enabled",
            "update_field": "is_retention_lock_enabled",
            "is_mutable": True,
        },
        {
            "param_name": source_id_param,
            "resource_field": source_id_param,
            "is_mutable": False,
        },
        {
            "param_name": "kms_key_id",
            "resource_field": "kms_key_id",
            "is_mutable": False,
            "immutable_reason": (
                "changing a backup's encryption key after create is not "
                "supported"
            ),
        },
    ]
