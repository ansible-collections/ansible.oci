# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_volume_backup_policy_assignment
short_description: Manage an OCI volume backup policy assignment
description:
  - Assign, replace, or remove a backup policy on a block volume, boot volume,
    or volume group by asset OCID.
version_added: "1.1.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  state:
    description:
      - Desired assignment state.
    type: str
    choices: [present, absent]
    default: present
  asset_id:
    description:
      - OCID of the block volume, boot volume, or volume group.
    type: str
    required: true
  policy_id:
    description:
      - OCID of the backup policy to assign.
      - Required for C(state=present). Ignored for C(state=absent).
      - Each asset has one assignment. Setting a different policy replaces
        the current assignment.
    type: str
notes:
  - OCI controls which policies are valid for each asset.
  - A volume whose policy is managed by its volume group cannot be changed
    separately. Manage the volume group's assignment instead.
"""

EXAMPLES = r"""
- name: Assign a backup policy to a block volume
  ansible.oci.oci_volume_backup_policy_assignment:
    asset_id: ocid1.volume.oc1..example
    policy_id: ocid1.volumebackuppolicy.oc1..example
  register: assignment

- name: Change the policy assigned to a boot volume
  ansible.oci.oci_volume_backup_policy_assignment:
    asset_id: ocid1.bootvolume.oc1..example
    policy_id: ocid1.volumebackuppolicy.oc1..other

- name: Assign a backup policy to a volume group
  ansible.oci.oci_volume_backup_policy_assignment:
    asset_id: ocid1.volumegroup.oc1..example
    policy_id: ocid1.volumebackuppolicy.oc1..example

- name: Remove the backup policy assignment
  ansible.oci.oci_volume_backup_policy_assignment:
    state: absent
    asset_id: ocid1.volume.oc1..example
"""

RETURN = r"""
resource:
  description: The current volume backup policy assignment.
  returned: when state=present and not in check mode
  type: dict
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

from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
    UpdateFieldSpec,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)

imported_oci_sdk = import_oci_sdk()
oci = imported_oci_sdk[0]
HAS_OCI_SDK = imported_oci_sdk[1]


class OciVolumeBackupPolicyAssignmentModule(OciResourceBase):
    @property
    def client_class(self):
        return oci.core.BlockstorageClient

    # asset_id selects an asset, not an existing assignment.
    resource_id_param = None
    name_lookup_param = None
    create_resource_name = "volume backup policy assignment"
    common_update_field_specs = ()
    update_field_specs = (UpdateFieldSpec(param_name="policy_id", is_mutable=True),)

    def get_resource_response(self, resource_id):
        return self.call_with_retry(
            self.client.get_volume_backup_policy_asset_assignment,
            asset_id=resource_id,
        )

    def get_current_assignment(self):
        try:
            response = self.get_resource_response(self.module.params["asset_id"])
        except oci.exceptions.ServiceError as exc:
            if exc.status == 404:
                return None
            raise
        return response.data[0] if response.data else None

    def resolve_target_resource(self):
        current = self.get_current_assignment()
        asset_id = self.module.params["asset_id"]
        if current is not None and current.asset_id != asset_id:
            self.module.fail_json(
                msg=(
                    f"The assignment returned for asset_id={asset_id} "
                    f"belongs to {current.asset_id}. Manage the volume group's "
                    "assignment instead."
                )
            )
        return current

    def create_assignment(self, policy_id):
        details = oci.core.models.CreateVolumeBackupPolicyAssignmentDetails(
            asset_id=self.module.params["asset_id"],
            policy_id=policy_id,
        )
        return self.call_with_retry(
            self.client.create_volume_backup_policy_assignment,
            create_volume_backup_policy_assignment_details=details,
        ).data

    def fail_oci_change(self, action, exc):
        message = (
            f"OCI could not {action} the backup policy assignment for "
            f"asset_id={self.module.params['asset_id']}: {exc}"
        )
        if getattr(exc, "status", None) in (400, 409):
            message += (
                ". If this volume's policy is controlled by a volume group, "
                "change the volume group's assignment instead"
            )
        self.module.fail_json(msg=message)

    def create_resource(self):
        try:
            return self.create_assignment(self.module.params["policy_id"])
        except oci.exceptions.ServiceError as exc:
            self.fail_oci_change("create", exc)

    def update_resource(self, resource):
        policy_id = self.get_update_plan(resource)["update_model_fields"]["policy_id"]
        try:
            return self.create_assignment(policy_id)
        except oci.exceptions.ServiceError as exc:
            self.fail_oci_change("replace", exc)

    def delete_resource(self, resource):
        try:
            return self.call_with_retry(
                self.client.delete_volume_backup_policy_assignment,
                policy_assignment_id=resource.id,
            ).data
        except oci.exceptions.ServiceError as exc:
            self.fail_oci_change("delete", exc)


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        asset_id=dict(type="str", required=True),
        policy_id=dict(type="str"),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[("state", "present", ["policy_id"])],
    )
    OciVolumeBackupPolicyAssignmentModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
