# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_volume_group_backup
short_description: Manage a volume group backup resource in Oracle Cloud Infrastructure
description:
  - Create, update, and delete OCI Block Volume group backups.
  - A volume group backup is a crash-consistent, point-in-time copy of every
    member volume in a volume group. It can be used to restore the group or
    create a new volume group.
  - Use M(oracle.oci.oci_volume_group_backup_info) to list or fetch volume
    group backups.
  - Uses the shared OCI helper layer for authentication, waiting, retry
    behavior, and result shaping.
  - Create requests must omit C(volume_group_backup_id). After create, capture
    the returned backup ID and use it for later C(state=present) and
    C(state=absent) tasks.
version_added: "1.1.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - oracle.oci.oci_auth_options
  - oracle.oci.oci_name_lookup_options
  - oracle.oci.oci_wait_options
  - oracle.oci.oci_tags_options
options:
  state:
    description:
      - The desired lifecycle state of the volume group backup.
    type: str
    choices: [present, absent]
    default: present
  volume_group_backup_id:
    description:
      - The OCID of the volume group backup.
      - When provided, the module manages this exact backup.
      - Required to distinguish between multiple backups that share the same
        scoped C(name).
    type: str
  name:
    description:
      - Human-readable name for the volume group backup.
      - Required when creating a backup.
      - When C(volume_group_backup_id) is omitted, the module uses
        C(compartment_id + volume_group_id + name) to find an existing backup.
      - If exactly one backup matches, C(state=present) manages it as the update
        target and C(state=absent) deletes it.
      - If more than one backup matches, the task fails and the caller must
        supply C(volume_group_backup_id).
    type: str
  compartment_id:
    description:
      - The OCID of the compartment that should contain the volume group backup.
      - Optional at create time. When omitted, OCI stores the backup in the
        source volume group's compartment.
      - Required to scope name-based backup lookups when
        C(volume_group_backup_id) is omitted, including the lookup that runs
        before create.
      - The module does not move an existing backup to another compartment.
    type: str
  volume_group_id:
    description:
      - The OCID of the volume group to back up.
      - Required when creating a backup.
      - Also scopes name-based backup lookups when C(volume_group_backup_id)
        is omitted.
      - Set only at create time; changing the source volume group of an
        existing backup is not supported, so a change is rejected.
    type: str
  type:
    description:
      - The type of backup to create.
      - C(full) copies every block on every member volume.
      - C(incremental) copies only the blocks that changed since the last
        backup of that volume group.
      - If omitted, OCI defaults to C(incremental). The returned C(type)
        field reports C(INCREMENTAL) or C(FULL) as stored, including when
        this is the first backup of the volume group.
      - Applied only at create time. The module does not compare this field
        after create, so rerunning a create task that includes C(type) is a
        no-op even though the resource stores C(FULL) or C(INCREMENTAL).
    type: str
    choices: [full, incremental]
  retention_period:
    description:
      - How long OCI keeps this backup before it expires.
      - Omit this to create a backup with no retention period, matching the
        console "no retention period" option.
      - Supports updates.
    type: dict
    suboptions:
      retention_time_amount:
        description:
          - Numeric length of the retention period. Combined with
            C(retention_time_unit) this is, for example, 30 days or 1 year.
        type: int
        required: true
      retention_time_unit:
        description:
          - Unit for C(retention_time_amount).
        type: str
        choices: [days, years]
        required: true
  prevent_deletion_enabled:
    description:
      - Whether the backup is protected from deletion during the configured
        retention period.
      - Returned by OCI as C(is_prevent_deletion_enabled).
      - When true, C(state=absent) fails until the retention period ends.
      - Supports updates.
    type: bool
  indefinite_retention_enabled:
    description:
      - Whether a legal hold keeps the backup from being modified or deleted,
        regardless of the retention period.
      - Matches the console "indefinite hold" option.
      - Returned by OCI as C(is_indefinite_retention_enabled).
      - When true, C(state=absent) fails until the hold is removed.
      - Supports updates.
    type: bool
  retention_lock_enabled:
    description:
      - Whether the retention period is locked so it cannot be shortened.
      - Use together with C(retention_period).
      - Returned by OCI as C(is_retention_lock_enabled).
      - Once enabled, this cannot be undone. After lock, the retention period
        can only be lengthened, not shortened or removed.
      - When true, C(state=absent) fails until the retention period expires.
        The lock itself cannot be cleared.
      - Supports updates.
    type: bool
notes:
  - Enabling C(retention_lock_enabled) cannot be undone. After lock, the
    retention period cannot be shortened or removed, and C(state=absent)
    fails until the retention period expires.
  - C(prevent_deletion_enabled) and C(indefinite_retention_enabled) prevent
    C(state=absent) from deleting the backup while they remain in effect.
  - Changing the source volume group of an existing backup is not supported.
"""

EXAMPLES = r"""
- name: Create a full backup of a volume group
  oracle.oci.oci_volume_group_backup:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    name: pre-maintenance-group-backup
    volume_group_id: ocid1.volumegroup.oc1..example
    type: full
  register: created_backup

- name: Create an incremental volume group backup
  oracle.oci.oci_volume_group_backup:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    name: nightly-group-backup
    volume_group_id: ocid1.volumegroup.oc1..example
    type: incremental

- name: Create a backup with a 30-day retention period and delete prevention
  oracle.oci.oci_volume_group_backup:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    name: retained-group-backup
    volume_group_id: ocid1.volumegroup.oc1..example
    type: full
    retention_period:
      retention_time_amount: 30
      retention_time_unit: days
    prevent_deletion_enabled: true
    retention_lock_enabled: true

- name: Reconcile a uniquely named backup by name (update tags)
  oracle.oci.oci_volume_group_backup:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    volume_group_id: ocid1.volumegroup.oc1..example
    name: pre-maintenance-group-backup
    freeform_tags:
      retention: 30d

- name: Delete the backup
  oracle.oci.oci_volume_group_backup:
    state: absent
    volume_group_backup_id: "{{ created_backup.resource.id }}"

- name: Delete a uniquely named backup without providing volume_group_backup_id
  oracle.oci.oci_volume_group_backup:
    state: absent
    compartment_id: ocid1.compartment.oc1..example
    volume_group_id: ocid1.volumegroup.oc1..example
    name: pre-maintenance-group-backup
"""

RETURN = r"""
resource:
  description: The volume group backup resource.
  returned: when state != absent
  type: dict
  contains:
    id:
      description: The OCID of the volume group backup.
      type: str
      returned: always
      sample: ocid1.volumegroupbackup.oc1..example
    name:
      description: The display name of the volume group backup.
      type: str
      returned: always
      sample: pre-maintenance-group-backup
    compartment_id:
      description: The OCID of the compartment containing the volume group backup.
      type: str
      returned: always
      sample: ocid1.compartment.oc1..example
    volume_group_id:
      description: The OCID of the source volume group.
      type: str
      returned: always
      sample: ocid1.volumegroup.oc1..example
    lifecycle_state:
      description: The current lifecycle state of the volume group backup.
      type: str
      returned: always
      sample: AVAILABLE
    type:
      description: The type of backup.
      type: str
      returned: always
      sample: FULL
    source_type:
      description: Whether the backup was created manually or by a scheduled policy.
      type: str
      returned: always
      sample: MANUAL
    size_in_gbs:
      description: The aggregate size of the source volume group, in GBs.
      type: int
      returned: always
      sample: 100
    size_in_mbs:
      description: The aggregate size of the source volume group, in MBs.
      type: int
      returned: always
      sample: 102400
    unique_size_in_gbs:
      description: The amount of space this backup consumes, in GBs.
      type: int
      returned: always
      sample: 20
    unique_size_in_mbs:
      description: The amount of space this backup consumes, in MBs.
      type: int
      returned: always
      sample: 20480
    volume_backup_ids:
      description: The OCIDs of the individual volume backups in this group backup.
      type: list
      elements: str
      returned: always
      sample:
        - ocid1.volumebackup.oc1..example1
        - ocid1.volumebackup.oc1..example2
    source_volume_group_backup_id:
      description:
        - The OCID of the source volume group backup when this backup was
          copied from another backup, if any.
      type: str
      returned: always
      sample: null
    expiration_time:
      description: The date and time the backup will expire and be deleted, in RFC3339 format.
      type: str
      returned: always
      sample: "2026-02-01T00:00:00.000Z"
    retention_period:
      description: Configured retention duration for the backup, if any.
      type: dict
      returned: always
      contains:
        retention_time_amount:
          description: Numeric length of the retention period.
          type: int
          sample: 30
        retention_time_unit:
          description: Unit for the retention amount.
          type: str
          sample: DAYS
    time_retention_expires_at:
      description:
        - When the backup's retention period ends and the backup is set to
          expire, in RFC3339 format.
      type: str
      returned: always
      sample: "2026-02-01T00:00:00.000Z"
    is_prevent_deletion_enabled:
      description: Whether deletion is prevented during the retention period.
      type: bool
      returned: always
      sample: true
    is_indefinite_retention_enabled:
      description: Whether a legal hold is applied to the backup.
      type: bool
      returned: always
      sample: false
    is_retention_lock_enabled:
      description: Whether the retention period is locked.
      type: bool
      returned: always
      sample: true
    freeform_tags:
      description: Free-form tags applied to the backup.
      type: dict
      returned: always
      sample: {"retention": "30d"}
    defined_tags:
      description: Defined tags applied to the backup.
      type: dict
      returned: always
      sample: {"Operations": {"CostCenter": "42"}}
    time_created:
      description: The date and time the backup was created, in RFC3339 format.
      type: str
      returned: always
      sample: "2026-01-01T00:00:00.000Z"
    time_request_received:
      description:
        - The date and time the backup request was received, in RFC3339 format.
      type: str
      returned: always
      sample: "2026-01-01T00:00:00.000Z"
  sample:
    id: ocid1.volumegroupbackup.oc1..example
    name: pre-maintenance-group-backup
    compartment_id: ocid1.compartment.oc1..example
    volume_group_id: ocid1.volumegroup.oc1..example
    lifecycle_state: AVAILABLE
    type: FULL
    source_type: MANUAL
    size_in_gbs: 100
    size_in_mbs: 102400
    unique_size_in_gbs: 20
    unique_size_in_mbs: 20480
    volume_backup_ids:
      - ocid1.volumebackup.oc1..example1
      - ocid1.volumebackup.oc1..example2
    source_volume_group_backup_id: null
    expiration_time: "2026-02-01T00:00:00.000Z"
    retention_period:
      retention_time_amount: 30
      retention_time_unit: DAYS
    time_retention_expires_at: "2026-02-01T00:00:00.000Z"
    is_prevent_deletion_enabled: true
    is_indefinite_retention_enabled: false
    is_retention_lock_enabled: true
    freeform_tags: {"retention": "30d"}
    defined_tags: {"Operations": {"CostCenter": "42"}}
    time_created: "2026-01-01T00:00:00.000Z"
    time_request_received: "2026-01-01T00:00:00.000Z"
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.oracle.oci.plugins.module_utils.oci_backup import (
    build_backup_update_field_specs,
)
from ansible_collections.oracle.oci.plugins.module_utils.oci_common import (
    LIFECYCLE_AVAILABLE,
    OCI_COMMON_ARGS,
    filter_none_values,
    import_oci_sdk,
    normalize_enum_values,
)
from ansible_collections.oracle.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
)

imported_oci_sdk = import_oci_sdk()
oci = imported_oci_sdk[0]
HAS_OCI_SDK = imported_oci_sdk[1]

CREATE_REQUIRED_FIELDS = [
    "volume_group_id",
    "name",
]
WAIT_FOR_BACKUP_STATES = [LIFECYCLE_AVAILABLE]

# Module inputs use lowercase snake_case choices (Ansible convention), while
# OCI's wire format uses upper-case constants (for example "full" -> "FULL").
# Assigned to OciVolumeGroupBackupModule.enum_keys so the shared "subset_dict"
# comparator (see oci_resource.py) normalizes retention_period the same way
# the create builder does.
ENUM_KEYS = frozenset({"type", "retention_time_unit"})


def build_retention_period(retention_period):
    if not retention_period:
        return None
    normalized = normalize_enum_values(retention_period, ENUM_KEYS)
    return oci.core.models.RetentionDuration(
        **filter_none_values(
            {
                "retention_time_amount": normalized.get("retention_time_amount"),
                "retention_time_unit": normalized.get("retention_time_unit"),
            }
        )
    )


def build_create_volume_group_backup_details(params):
    details = filter_none_values(
        {
            "volume_group_id": params.get("volume_group_id"),
            "compartment_id": params.get("compartment_id"),
            "display_name": params.get("name"),
            "type": normalize_enum_values(
                {"type": params.get("type")}, ENUM_KEYS
            )["type"],
            "retention_period": build_retention_period(
                params.get("retention_period")
            ),
            "is_prevent_deletion_enabled": params.get(
                "prevent_deletion_enabled"
            ),
            "is_indefinite_retention_enabled": params.get(
                "indefinite_retention_enabled"
            ),
            "is_retention_lock_enabled": params.get(
                "retention_lock_enabled"
            ),
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
        }
    )
    return oci.core.models.CreateVolumeGroupBackupDetails(**details)


# For updates, the shared planner records the raw parameter values in the update
# model; these builders convert them into the SDK model objects the update call
# expects, mirroring the create path (see oci_blockstorage_volume.py).
NESTED_UPDATE_BUILDERS = {
    "retention_period": build_retention_period,
}


class OciVolumeGroupBackupModule(OciResourceBase):
    """Concrete resource adapter for OCI volume group backups."""

    @property
    def client_class(self):
        return oci.core.BlockstorageClient

    resource_id_param = "volume_group_backup_id"
    list_resource_method = "list_volume_group_backups"
    list_filter_params = ("volume_group_id",)
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "volume group backup"
    update_method_name = "update_volume_group_backup"
    update_details_name = "update_volume_group_backup_details"
    update_wait_states = WAIT_FOR_BACKUP_STATES
    enum_keys = ENUM_KEYS
    # type is create-only and uses a case-normalized enum ("full" vs "FULL").
    # Including it in drift detection would false-positive on create-task
    # reruns, so it is omitted. volume_group_id is compared like
    # oci_volume_backup's create-only identity field. kms_key_id is omitted
    # because CreateVolumeGroupBackupDetails has no encryption-key field.
    update_field_specs = build_backup_update_field_specs(
        "volume_group_id",
        exclude=("kms_key_id",),
        extra_immutable=("compartment_id",),
    )

    def get_resource_response(self, resource_id):
        return self.call_with_retry(
            self.client.get_volume_group_backup,
            volume_group_backup_id=resource_id,
        )

    def create_resource(self):
        create_volume_group_backup_details = build_create_volume_group_backup_details(
            self.module.params
        )
        response = self.call_with_retry(
            self.client.create_volume_group_backup,
            create_volume_group_backup_details=create_volume_group_backup_details,
        )
        return self.get_mutation_result(
            response.data,
            getattr(response.data, "id", None),
            WAIT_FOR_BACKUP_STATES,
        )

    def build_update_details(self, update_model_fields):
        update_model_fields = dict(update_model_fields)
        for field_name, builder in NESTED_UPDATE_BUILDERS.items():
            if field_name in update_model_fields:
                update_model_fields[field_name] = builder(
                    update_model_fields[field_name]
                )
        return oci.core.models.UpdateVolumeGroupBackupDetails(**update_model_fields)

    def delete_resource(self, resource):
        return self.delete_resource_and_wait(
            resource,
            self.client.delete_volume_group_backup,
            volume_group_backup_id=resource.id,
        )


def main():
    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        volume_group_backup_id=dict(type="str"),
        volume_group_id=dict(type="str"),
        type=dict(type="str", choices=["full", "incremental"]),
        retention_period=dict(
            type="dict",
            options=dict(
                retention_time_amount=dict(type="int", required=True),
                retention_time_unit=dict(
                    type="str",
                    choices=["days", "years"],
                    required=True,
                ),
            ),
        ),
        prevent_deletion_enabled=dict(type="bool"),
        indefinite_retention_enabled=dict(type="bool"),
        retention_lock_enabled=dict(type="bool"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    OciVolumeGroupBackupModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
