# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_volume_group_backup_info
short_description: Retrieve block volume group backup information from Oracle Cloud Infrastructure
description:
  - Retrieve details about one or more OCI block volume group backups.
  - Use C(volume_group_backup_id) to fetch a single backup, or C(compartment_id) to
    list backups in a compartment.
  - This is a read-only module and does not modify resources.
version_added: "1.0.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - oracle.oci.oci_auth_options
  - oracle.oci.oci_info_filter_options
options:
  compartment_id:
    description:
      - The OCID of the compartment to list volume group backups from.
      - Required when listing resources.
    type: str
  volume_group_backup_id:
    description:
      - The OCID of a specific volume group backup to retrieve.
      - When specified, returns a single resource instead of a list.
    type: str
  volume_group_id:
    description:
      - Filter listed backups by the OCID of their source volume group.
      - Only used when C(compartment_id) is provided.
    type: str
"""

EXAMPLES = r"""
- name: List all volume group backups in a compartment
  oracle.oci.oci_volume_group_backup_info:
    compartment_id: ocid1.compartment.oc1..example

- name: List volume group backups for a specific volume
  oracle.oci.oci_volume_group_backup_info:
    compartment_id: ocid1.compartment.oc1..example
    volume_group_id: ocid1.volume.oc1..example

- name: List volume group backups in a compartment by name
  oracle.oci.oci_volume_group_backup_info:
    compartment_id: ocid1.compartment.oc1..example
    name: pre-maintenance-backup

- name: Get a specific volume group backup
  oracle.oci.oci_volume_group_backup_info:
    volume_group_backup_id: ocid1.volumebackup.oc1..example
"""

RETURN = r"""
volume_group_backups:
  description: List of volume group backups that matched the query.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The OCID of the volume group backup.
      type: str
      returned: always
      sample: ocid1.volumebackup.oc1..example
    name:
      description: The display name of the volume group backup.
      type: str
      returned: always
      sample: pre-maintenance-backup
    compartment_id:
      description: The OCID of the compartment containing the volume group backup.
      type: str
      returned: always
      sample: ocid1.compartment.oc1..example
    volume_group_id:
      description: The OCID of the source volume group.
      type: str
      returned: always
      sample: ocid1.volume.oc1..example
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
      description: The size of the source volume, in GBs.
      type: int
      returned: always
      sample: 50
    size_in_mbs:
      description: The size of the source volume, in MBs.
      type: int
      returned: always
      sample: 51200
    unique_size_in_gbs:
      description: The amount of space this backup consumes, in GBs.
      type: int
      returned: always
      sample: 10
    unique_size_in_mbs:
      description: The amount of space this backup consumes, in MBs.
      type: int
      returned: always
      sample: 1
    source_volume_group_backup_id:
      description:
        - The OCID of the source volume group backup when this backup was copied
          from another backup, if any.
      type: str
      returned: always
      sample: null
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
    system_tags:
      description: System tags applied to the backup by OCI.
      type: dict
      returned: always
      sample: {}
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
    - id: ocid1.volumebackup.oc1..example
      name: pre-maintenance-backup
      compartment_id: ocid1.compartment.oc1..example
      volume_group_id: ocid1.volume.oc1..example
      lifecycle_state: AVAILABLE
      type: FULL
      source_type: MANUAL
      size_in_gbs: 50
      size_in_mbs: 51200
      unique_size_in_gbs: 10
      unique_size_in_mbs: 1
      source_volume_group_backup_id: null
      expiration_time: "2026-02-01T00:00:00.000Z"
      kms_key_id: ocid1.key.oc1..example
      retention_period:
        retention_time_amount: 30
        retention_time_unit: DAYS
      time_retention_expires_at: "2026-02-01T00:00:00.000Z"
      is_prevent_deletion_enabled: true
      is_indefinite_retention_enabled: false
      is_retention_lock_enabled: true
      freeform_tags: {"retention": "30d"}
      defined_tags: {"Operations": {"CostCenter": "42"}}
      system_tags: {}
      time_created: "2026-01-01T00:00:00.000Z"
      time_request_received: "2026-01-01T00:00:00.000Z"
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.oracle.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)
from ansible_collections.oracle.oci.plugins.module_utils.oci_info import (
    OciInfoBase,
)

imported_oci_sdk = import_oci_sdk()
oci = imported_oci_sdk[0]
HAS_OCI_SDK = imported_oci_sdk[1]


class OciVolumeGroupBackupInfoModule(OciInfoBase):
    """Concrete info adapter for OCI block volume group backups."""

    @property
    def client_class(self):
        return oci.core.BlockstorageClient

    results_key = "volume_group_backups"
    resource_id_param = "volume_group_backup_id"
    resource_get_method = "get_volume_group_backup"
    list_resource_method = "list_volume_group_backups"
    list_filter_params = [
        "compartment_id",
        "volume_group_id",
        "lifecycle_state",
    ]


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        compartment_id=dict(type="str"),
        volume_group_backup_id=dict(type="str"),
        volume_group_id=dict(type="str"),
        name=dict(type="str"),
        lifecycle_state=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["compartment_id", "volume_group_backup_id"]],
    )

    OciVolumeGroupBackupInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
