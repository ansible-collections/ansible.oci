# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_boot_volume_backup
short_description: Manage a boot volume backup resource in Oracle Cloud Infrastructure
description:
  - Create, update, and delete OCI boot volume backups.
  - A boot volume backup is a point-in-time copy of a boot volume's data that
    can be used to restore the OS disk or create new boot volumes.
  - Boot volume backups use a separate OCI API from block (data) volume backups;
    use M(oracle.oci.oci_volume_backup) for block volumes.
  - Use M(oracle.oci.oci_boot_volume_backup_info) to list or fetch boot volume
    backups.
  - Uses the shared OCI helper layer for authentication, waiting, retry
    behavior, and result shaping.
  - Create requests must omit C(boot_volume_backup_id). After create, capture
    the returned backup ID and use it for later C(state=present) and
    C(state=absent) tasks.
version_added: "1.0.0"
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
      - The desired lifecycle state of the boot volume backup.
    type: str
    choices: [present, absent]
    default: present
  boot_volume_backup_id:
    description:
      - The OCID of the boot volume backup.
      - When provided, the module manages this exact backup.
      - Required to distinguish between multiple backups that share the same
        scoped C(name).
    type: str
  name:
    description:
      - Human-readable name for the boot volume backup.
      - Required when creating a backup.
      - When C(boot_volume_backup_id) is omitted, the module uses
        C(compartment_id + name) to find an existing backup.
      - If exactly one backup matches, C(state=present) manages it as the update
        target and C(state=absent) deletes it.
      - If more than one backup matches, the task fails and the caller must
        supply C(boot_volume_backup_id).
    type: str
  compartment_id:
    description:
      - The OCID of the compartment to scope name-based backup lookups to when
        C(boot_volume_backup_id) is omitted.
      - Not used when creating a backup; a new backup inherits the compartment
        of its source boot volume.
    type: str
  boot_volume_id:
    description:
      - The OCID of the boot volume to back up.
      - Required when creating a backup.
      - The module does not update this field after create.
    type: str
  type:
    description:
      - The type of backup to create.
      - C(incremental) only stores the blocks that changed since the last
        backup, while C(full) stores all blocks.
      - The module does not update this field after create.
    type: str
    choices: [full, incremental]
  kms_key_id:
    description:
      - The OCID of the Vault service key used to encrypt the backup.
      - The module does not update this field after create.
    type: str
"""

EXAMPLES = r"""
- name: Create a full backup of a boot volume before maintenance
  oracle.oci.oci_boot_volume_backup:
    state: present
    name: pre-maintenance-boot-backup
    boot_volume_id: ocid1.bootvolume.oc1..example
    type: full
  register: created_backup

- name: Create an incremental boot volume backup
  oracle.oci.oci_boot_volume_backup:
    state: present
    name: nightly-boot-backup
    boot_volume_id: ocid1.bootvolume.oc1..example
    type: incremental

- name: Reconcile a uniquely named boot volume backup by name (update tags)
  oracle.oci.oci_boot_volume_backup:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    name: pre-maintenance-boot-backup
    freeform_tags:
      retention: 30d

- name: Delete the boot volume backup
  oracle.oci.oci_boot_volume_backup:
    state: absent
    boot_volume_backup_id: "{{ created_backup.resource.id }}"

- name: Delete a uniquely named boot volume backup without providing its id
  oracle.oci.oci_boot_volume_backup:
    state: absent
    compartment_id: ocid1.compartment.oc1..example
    name: pre-maintenance-boot-backup
"""

RETURN = r"""
resource:
  description: The boot volume backup resource.
  returned: when state != absent
  type: dict
  contains:
    id:
      description: The OCID of the boot volume backup.
      type: str
      returned: always
      sample: ocid1.bootvolumebackup.oc1..example
    name:
      description: The display name of the boot volume backup.
      type: str
      returned: always
      sample: pre-maintenance-boot-backup
    compartment_id:
      description: The OCID of the compartment containing the boot volume backup.
      type: str
      returned: always
      sample: ocid1.compartment.oc1..example
    boot_volume_id:
      description: The OCID of the source boot volume.
      type: str
      returned: always
      sample: ocid1.bootvolume.oc1..example
    lifecycle_state:
      description: The current lifecycle state of the boot volume backup.
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
    image_id:
      description: The OCID of the image from which the source boot volume was created, if any.
      type: str
      returned: always
      sample: ocid1.image.oc1..example
    size_in_gbs:
      description: The size of the source boot volume, in GBs.
      type: int
      returned: always
      sample: 50
    unique_size_in_gbs:
      description: The amount of space this backup consumes, in GBs.
      type: int
      returned: always
      sample: 10
    expiration_time:
      description: The date and time the backup will expire and be deleted, in RFC3339 format.
      type: str
      returned: always
      sample: "2026-02-01T00:00:00.000Z"
    kms_key_id:
      description: The OCID of the Vault key used to encrypt the backup, if any.
      type: str
      returned: always
      sample: ocid1.key.oc1..example
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
  sample:
    id: ocid1.bootvolumebackup.oc1..example
    name: pre-maintenance-boot-backup
    compartment_id: ocid1.compartment.oc1..example
    boot_volume_id: ocid1.bootvolume.oc1..example
    lifecycle_state: AVAILABLE
    type: FULL
    source_type: MANUAL
    size_in_gbs: 50
    unique_size_in_gbs: 10
    freeform_tags: {"retention": "30d"}
    defined_tags: {"Operations": {"CostCenter": "42"}}
    time_created: "2026-01-01T00:00:00.000Z"
"""

from ansible.module_utils.basic import AnsibleModule

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
    "boot_volume_id",
    "name",
]
WAIT_FOR_BACKUP_STATES = [LIFECYCLE_AVAILABLE]

# Module inputs use lowercase snake_case choices (Ansible convention), while
# OCI's wire format uses upper-case constants (for example "full" -> "FULL").
ENUM_KEYS = {"type"}


def build_create_boot_volume_backup_details(params):
    details = filter_none_values(
        {
            "boot_volume_id": params.get("boot_volume_id"),
            "display_name": params.get("name"),
            "type": normalize_enum_values(
                {"type": params.get("type")}, ENUM_KEYS
            )["type"],
            "kms_key_id": params.get("kms_key_id"),
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
        }
    )
    return oci.core.models.CreateBootVolumeBackupDetails(**details)


class OciBootVolumeBackupModule(OciResourceBase):
    """Concrete resource adapter for OCI boot volume backups."""

    @property
    def client_class(self):
        return oci.core.BlockstorageClient

    resource_id_param = "boot_volume_backup_id"
    list_resource_method = "list_boot_volume_backups"
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "boot volume backup"
    update_method_name = "update_boot_volume_backup"
    update_details_name = "update_boot_volume_backup_details"
    update_wait_states = WAIT_FOR_BACKUP_STATES
    # boot_volume_id, type, and kms_key_id are create-only. They either have no
    # update counterpart or use a case-normalized enum whose raw module value
    # would false-positive against the upper-case resource field, so they are
    # excluded from drift detection to keep create-task reruns idempotent.
    update_field_specs = [
        {
            "param_name": "name",
            "resource_field": "display_name",
            "update_field": "display_name",
            "is_mutable": True,
        },
    ]

    def get_resource_response(self, resource_id):
        return self.call_with_retry(
            self.client.get_boot_volume_backup,
            boot_volume_backup_id=resource_id,
        )

    def create_resource(self):
        create_boot_volume_backup_details = build_create_boot_volume_backup_details(
            self.module.params
        )
        response = self.call_with_retry(
            self.client.create_boot_volume_backup,
            create_boot_volume_backup_details=create_boot_volume_backup_details,
        )
        return self.get_mutation_result(
            response.data,
            getattr(response.data, "id", None),
            WAIT_FOR_BACKUP_STATES,
        )

    def build_update_details(self, update_model_fields):
        return oci.core.models.UpdateBootVolumeBackupDetails(**update_model_fields)

    def delete_resource(self, resource):
        return self.delete_resource_and_wait(
            resource,
            self.client.delete_boot_volume_backup,
            boot_volume_backup_id=resource.id,
        )


def main():
    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        boot_volume_backup_id=dict(type="str"),
        boot_volume_id=dict(type="str"),
        type=dict(type="str", choices=["full", "incremental"]),
        kms_key_id=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    OciBootVolumeBackupModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
