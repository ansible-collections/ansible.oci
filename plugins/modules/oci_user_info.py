# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_user_info
short_description: Retrieve users from an OCI IAM identity domain
description:
  - Gets a user by SCIM identifier or lists users through the OCI IAM Identity Domains SCIM API.
version_added: "1.1.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  domain_id:
    description: OCID of the identity domain.
    type: str
  domain_url:
    description: Service endpoint of the identity domain.
    type: str
  user_id:
    description: SCIM identifier of a specific user.
    type: str
  user_name:
    description: Exact login-name filter.
    type: str
  name:
    description: Exact display-name filter.
    type: str
  active:
    description: Filter by enabled status.
    type: bool
"""

EXAMPLES = r"""
- name: List active users in an identity domain
  ansible.oci.oci_user_info:
    domain_id: ocid1.domain.oc1..example
    active: true

- name: Get one user
  ansible.oci.oci_user_info:
    domain_url: https://idcs-example.identity.oraclecloud.com
    user_id: 0123456789abcdef
"""

RETURN = r"""
users:
  description: Users matching the query.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: SCIM identifier.
      type: str
    ocid:
      description: OCI identifier, when exposed by the identity domain.
      type: str
    domain_id:
      description: OCID of the identity domain containing the user.
      type: str
    user_name:
      description: Login name.
      type: str
    name:
      description: Display name of the user.
      type: str
    given_name:
      description: Given name of the user, if present.
      type: str
    family_name:
      description: Family name of the user, if present.
      type: str
    email:
      description: Work email address, if present.
      type: str
    description:
      description: Description of the user, if present.
      type: str
    active:
      description: Whether the user can sign in.
      type: bool
    freeform_tags:
      description: Freeform tags on the user.
      type: dict
    defined_tags:
      description: Defined tags on the user, including tags applied automatically by OCI.
      type: dict
    time_created:
      description: User creation time from SCIM metadata, if present.
      type: str
    time_modified:
      description: Last modification time from SCIM metadata, if present.
      type: str
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import OCI_AUTH_ARGS
from ansible_collections.ansible.oci.plugins.module_utils.oci_identity_domains import (
    OCI_IDENTITY_DOMAIN_ARGS,
    OciIdentityDomainsMixin,
    escape_scim_filter_value,
    serialize_user,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import OciInfoBase


class OciUserInfoModule(OciIdentityDomainsMixin, OciInfoBase):
    results_key = "users"

    def serialize_result_resource(self, resource):
        return serialize_user(resource)

    def fetch_resources(self):
        user_id = self.module.params.get("user_id")
        if user_id:
            return self.get_resource_by_id(
                user_id, self.client.get_user, user_id=user_id
            )
        filters = []
        for param_name, attribute in (
            ("user_name", "userName"),
            ("name", "displayName"),
        ):
            value = self.module.params.get(param_name)
            if value is not None:
                filters.append(f'{attribute} eq "{escape_scim_filter_value(value)}"')
        active = self.module.params.get("active")
        if active is not None:
            filters.append(f"active eq {'true' if active else 'false'}")
        kwargs = {"filter": " and ".join(filters)} if filters else {}
        return self.list_all_resources(self.client.list_users, **kwargs)


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        **OCI_IDENTITY_DOMAIN_ARGS,
        user_id=dict(type="str"),
        user_name=dict(type="str"),
        name=dict(type="str"),
        active=dict(type="bool"),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["domain_id", "domain_url"]],
        mutually_exclusive=[["domain_id", "domain_url"]],
    )
    OciUserInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
