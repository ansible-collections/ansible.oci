# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_user_group_membership_info
short_description: Retrieve user group memberships from an OCI IAM identity domain
description:
  - Lists direct memberships for a user, a group, or a user and group pair
    through the OCI IAM Identity Domains SCIM API.
  - A group query returns its direct members. A user query returns its direct groups.
  - A query for a missing user or group returns an empty list.
version_added: "1.1.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  domain_id:
    description:
      - OCID of the identity domain.
      - Exactly one of C(domain_id) or C(domain_url) is required for every query.
    type: str
  domain_url:
    description:
      - Service endpoint of the identity domain.
      - Exactly one of C(domain_id) or C(domain_url) is required for every query.
    type: str
  user_id:
    description:
      - SCIM identifier of a user. At least one of C(user_id) or C(group_id) is required.
      - Alone, returns the user's direct groups; with C(group_id), filters that group's members to this user.
    type: str
  group_id:
    description:
      - SCIM identifier of a group. At least one of C(user_id) or C(group_id) is required.
      - Alone, returns the group's direct members; with C(user_id), returns the matching membership if present.
    type: str
"""

EXAMPLES = r"""
- name: Test whether a user belongs directly to a group
  ansible.oci.oci_user_group_membership_info:
    domain_id: ocid1.domain.oc1..example
    user_id: 0123456789abcdef
    group_id: fedcba9876543210

- name: List a user's direct groups
  ansible.oci.oci_user_group_membership_info:
    domain_url: https://idcs-example.identity.oraclecloud.com
    user_id: 0123456789abcdef
"""

RETURN = r"""
user_group_memberships:
  description: Direct memberships matching the query.
  returned: always
  type: list
  elements: dict
  contains:
    group_id:
      description: Group SCIM identifier.
      type: str
    user_id:
      description: User SCIM identifier.
      type: str
    user_ocid:
      description: User OCID for group queries, when exposed by the identity domain.
      type: str
    group_ocid:
      description: Group OCID for user queries, when exposed by the identity domain.
      type: str
    membership_ocid:
      description: Membership OCID, when exposed by the identity domain.
      type: str
    display_name:
      description: Display name of the returned user or group, when available.
      type: str
    type:
      description: SCIM membership type.
      type: str
    date_added:
      description: Time the membership was added, when available.
      type: str
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import OCI_AUTH_ARGS
from ansible_collections.ansible.oci.plugins.module_utils.oci_identity_domains import (
    OCI_IDENTITY_DOMAIN_ARGS,
    OciIdentityDomainsMixin,
    serialize_membership,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import OciInfoBase


class OciUserGroupMembershipInfoModule(OciIdentityDomainsMixin, OciInfoBase):
    results_key = "user_group_memberships"

    def serialize_result_resource(self, resource):
        group_id = self.module.params.get("group_id")
        if group_id:
            return serialize_membership(resource, group_id)
        result = serialize_membership(
            resource, resource.value, self.module.params["user_id"]
        )
        result["group_ocid"] = result.pop("user_ocid")
        return result

    def fetch_resources(self):
        user_id = self.module.params.get("user_id")
        group_id = self.module.params.get("group_id")
        if group_id:
            groups = self.get_resource_by_id(
                group_id,
                self.client.get_group,
                group_id=group_id,
                attributes="members",
            )
            if not groups:
                return []
            members = getattr(groups[0], "members", None) or []
            if user_id:
                members = [
                    member
                    for member in members
                    if getattr(member, "value", None) == user_id
                ]
            return members

        users = self.get_resource_by_id(
            user_id, self.client.get_user, user_id=user_id, attributes="groups"
        )
        if not users:
            return []
        return [
            group
            for group in (getattr(users[0], "groups", None) or [])
            if getattr(group, "type", None) in (None, "direct")
        ]


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        **OCI_IDENTITY_DOMAIN_ARGS,
        user_id=dict(type="str"),
        group_id=dict(type="str"),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[
            ["domain_id", "domain_url"],
            ["user_id", "group_id"],
        ],
        mutually_exclusive=[["domain_id", "domain_url"]],
    )
    OciUserGroupMembershipInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
