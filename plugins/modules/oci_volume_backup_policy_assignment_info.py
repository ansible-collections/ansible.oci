# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_volume_backup_policy_assignment_info
short_description: Retrieve an OCI volume backup policy assignment
description:
  - Read the backup policy assignment for a block volume, boot volume, or
    volume group by asset OCID, or retrieve one by assignment OCID.
version_added: "1.1.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  asset_id:
    description:
      - OCID of the block volume, boot volume, or volume group whose
        assignment should be retrieved.
      - Exactly one of C(asset_id) and C(volume_backup_policy_assignment_id)
        must be provided.
    type: str
  volume_backup_policy_assignment_id:
    description:
      - OCID of a specific backup policy assignment.
      - Exactly one of C(asset_id) and C(volume_backup_policy_assignment_id)
        must be provided.
    type: str
"""

EXAMPLES = r"""
- name: Get the policy assignment for a block volume
  ansible.oci.oci_volume_backup_policy_assignment_info:
    asset_id: ocid1.volume.oc1..example

- name: Get a specific policy assignment
  ansible.oci.oci_volume_backup_policy_assignment_info:
    volume_backup_policy_assignment_id: ocid1.volumebackuppolicyassignment.oc1..example
"""

RETURN = r"""
volume_backup_policy_assignments:
  description: Assignments matching the requested asset or assignment OCID.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: OCID of the assignment.
      type: str
      returned: always
      sample: ocid1.volumebackuppolicyassignment.oc1..example
    asset_id:
      description: OCID of the assigned asset.
      type: str
      returned: always
      sample: ocid1.volume.oc1..example
    policy_id:
      description: OCID of the assigned policy.
      type: str
      returned: always
      sample: ocid1.volumebackuppolicy.oc1..example
    time_created:
      description: Assignment creation time in RFC3339 format.
      type: str
      returned: always
      sample: "2026-09-27T00:00:00Z"
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import OciInfoBase

imported_oci_sdk = import_oci_sdk()
oci = imported_oci_sdk[0]
HAS_OCI_SDK = imported_oci_sdk[1]


class OciVolumeBackupPolicyAssignmentInfoModule(OciInfoBase):
    @property
    def client_class(self):
        return oci.core.BlockstorageClient

    results_key = "volume_backup_policy_assignments"
    resource_id_param = "volume_backup_policy_assignment_id"
    resource_id_kwarg = "policy_assignment_id"
    resource_get_method = "get_volume_backup_policy_assignment"

    def fetch_resources(self):
        if self.module.params.get(self.resource_id_param):
            return super().fetch_resources()
        try:
            response = self.call_with_retry(
                self.client.get_volume_backup_policy_asset_assignment,
                asset_id=self.module.params["asset_id"],
            )
        except oci.exceptions.ServiceError as exc:
            if exc.status == 404:
                return []
            raise
        return response.data


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        asset_id=dict(type="str"),
        volume_backup_policy_assignment_id=dict(type="str"),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["asset_id", "volume_backup_policy_assignment_id"]],
        mutually_exclusive=[["asset_id", "volume_backup_policy_assignment_id"]],
    )
    OciVolumeBackupPolicyAssignmentInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
