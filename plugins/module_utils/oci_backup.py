"""Shared helpers for OCI volume, boot-volume, and volume-group backup modules."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    UpdateFieldSpec,
)


def build_backup_update_field_specs(
    source_id_param, exclude=(), extra_immutable=()
):
    """Return update-planner specs shared by OCI backup modules.

    ``source_id_param`` is the create-only source identity field
    (``volume_id``, ``boot_volume_id``, or ``volume_group_id``). Name,
    retention flags, and ``kms_key_id`` are identical across volume and
    boot-volume backup APIs.

    ``exclude`` drops specs by ``param_name`` (volume group backups have
    no ``kms_key_id``). ``extra_immutable`` appends create-only identity
    fields such as ``compartment_id``.
    """
    specs = [
        UpdateFieldSpec(
            param_name="name",
            resource_field="display_name",
            is_mutable=True,
        ),
        UpdateFieldSpec(
            param_name="retention_period",
            is_mutable=True,
            compare="subset_dict",
        ),
        UpdateFieldSpec(
            param_name="prevent_deletion_enabled",
            resource_field="is_prevent_deletion_enabled",
            is_mutable=True,
        ),
        UpdateFieldSpec(
            param_name="indefinite_retention_enabled",
            resource_field="is_indefinite_retention_enabled",
            is_mutable=True,
        ),
        UpdateFieldSpec(
            param_name="retention_lock_enabled",
            resource_field="is_retention_lock_enabled",
            is_mutable=True,
        ),
        UpdateFieldSpec(param_name=source_id_param, is_mutable=False),
        UpdateFieldSpec(
            param_name="kms_key_id",
            is_mutable=False,
            immutable_reason=(
                "changing a backup's encryption key after create is not "
                "supported"
            ),
        ),
    ]
    specs = [spec for spec in specs if spec.param_name not in exclude]
    specs.extend(
        UpdateFieldSpec(param_name=param_name, is_mutable=False)
        for param_name in extra_immutable
    )
    return tuple(specs)
