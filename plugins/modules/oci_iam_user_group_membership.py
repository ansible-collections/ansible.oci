# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_iam_user_group_membership
short_description: Manage a user group membership in an OCI IAM identity domain
description:
  - Adds or removes a user from a group through the OCI IAM Identity Domains SCIM API.
  - A membership is identified by C(domain_id) or C(domain_url), C(group_id), and C(user_id).
version_added: "1.1.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  state:
    description:
      - C(present) adds the user to the group if the membership is missing.
      - C(absent) removes the user from the group if the membership exists.
    type: str
    choices: [present, absent]
    default: present
  domain_id:
    description:
      - OCID of the identity domain.
      - Exactly one of C(domain_id) or C(domain_url) is required for either state.
    type: str
  domain_url:
    description:
      - Service endpoint of the identity domain.
      - Exactly one of C(domain_id) or C(domain_url) is required for either state.
    type: str
  user_id:
    description: SCIM identifier of the user. Required for both C(present) and C(absent).
    type: str
    required: true
  group_id:
    description: SCIM identifier of the group. Required for both C(present) and C(absent).
    type: str
    required: true
"""

EXAMPLES = r"""
- name: Add a user to a group
  ansible.oci.oci_iam_user_group_membership:
    domain_id: ocid1.domain.oc1..example
    user_id: 0123456789abcdef
    group_id: fedcba9876543210

- name: Remove a user from a group
  ansible.oci.oci_iam_user_group_membership:
    domain_url: https://idcs-example.identity.oraclecloud.com
    state: absent
    user_id: 0123456789abcdef
    group_id: fedcba9876543210
"""

RETURN = r"""
resource:
  description: The direct user group membership.
  returned: when state is present and check mode is off
  type: dict
  contains:
    group_id:
      description: Group SCIM identifier.
      type: str
    user_id:
      description: User SCIM identifier.
      type: str
    user_ocid:
      description: User OCID, when exposed by the identity domain.
      type: str
    membership_ocid:
      description: Membership OCID, when exposed by the identity domain.
      type: str
    display_name:
      description: Display name of the group member, when available.
      type: str
    type:
      description: SCIM member type.
      type: str
    date_added:
      description: Time the member was added, when available.
      type: str
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_identity_domains import (
    OCI_IDENTITY_DOMAIN_ARGS,
    OciIdentityDomainResourceBase,
    build_operation,
    build_patch_op,
    serialize_membership,
)

oci = import_oci_sdk()[0]


def build_group_member(params):
    return oci.identity_domains.models.GroupMembers(
        value=params["user_id"], type="User"
    )


class OciIamUserGroupMembershipModule(OciIdentityDomainResourceBase):
    resource_id_param = None
    name_lookup_param = None
    create_required_fields = ("user_id", "group_id")
    create_resource_name = "user group membership"

    def serialize_result_resource(self, resource):
        return serialize_membership(
            resource,
            self.module.params["group_id"],
            self.module.params["user_id"],
        )

    def _find_member(self, group):
        if group is None:
            return None
        user_id = self.module.params["user_id"]
        return next(
            (
                member
                for member in (getattr(group, "members", None) or [])
                if getattr(member, "value", None) == user_id
            ),
            None,
        )

    def resolve_target_resource(self):
        group = self.get_resource_by_id(self.module.params["group_id"])
        return self._find_member(group)

    def validate_delete_request(self):
        self._require_create_fields()

    def get_resource_response(self, resource_id):
        return self.call_with_retry(
            self.client.get_group, group_id=resource_id, attributes="members"
        )

    def create_resource(self):
        member = build_group_member(self.module.params)
        response = self.call_with_retry(
            self.client.patch_group,
            group_id=self.module.params["group_id"],
            patch_op=build_patch_op(
                [build_operation("ADD", "members", [member])]
            ),
            attributes="members",
        )
        return self._find_member(response.data) or member

    def delete_resource(self, resource):
        member = build_group_member(self.module.params)
        self.call_with_retry(
            self.client.patch_group,
            group_id=self.module.params["group_id"],
            patch_op=build_patch_op(
                [build_operation("REMOVE", "members", [member])]
            ),
        )


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        **OCI_IDENTITY_DOMAIN_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        user_id=dict(type="str", required=True),
        group_id=dict(type="str", required=True),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["domain_id", "domain_url"]],
        mutually_exclusive=[["domain_id", "domain_url"]],
    )
    OciIamUserGroupMembershipModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
