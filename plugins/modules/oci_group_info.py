# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_group_info
short_description: Retrieve groups from an OCI IAM identity domain
description:
  - Gets a group by SCIM identifier or lists groups through the OCI IAM Identity Domains SCIM API.
version_added: "1.1.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  domain_id:
    description: OCID of the identity domain. Mutually exclusive with C(domain_url).
    type: str
  domain_url:
    description: Service endpoint of the identity domain. Mutually exclusive with C(domain_id).
    type: str
  group_id:
    description: SCIM identifier of a specific group.
    type: str
  display_name:
    description: Exact display-name filter.
    type: str
"""

EXAMPLES = r"""
- name: List groups by display name
  ansible.oci.oci_group_info:
    domain_id: ocid1.domain.oc1..example
    display_name: application-admins

- name: Get one group
  ansible.oci.oci_group_info:
    domain_url: https://idcs-example.identity.oraclecloud.com
    group_id: 0123456789abcdef
"""

RETURN = r"""
groups:
  description: Groups matching the query.
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
      description: OCID of the identity domain containing the group.
      type: str
    display_name:
      description: Display name.
      type: str
    freeform_tags:
      description: Freeform tags on the group.
      type: dict
    defined_tags:
      description: Defined tags on the group, including tags applied automatically by OCI.
      type: dict
    time_created:
      description: Group creation time from SCIM metadata, if present.
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
    serialize_group,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import OciInfoBase


class OciGroupInfoModule(OciIdentityDomainsMixin, OciInfoBase):
    results_key = "groups"

    def serialize_result_resource(self, resource):
        return serialize_group(resource)

    def fetch_resources(self):
        group_id = self.module.params.get("group_id")
        if group_id:
            return self.get_resource_by_id(
                group_id, self.client.get_group, group_id=group_id
            )
        display_name = self.module.params.get("display_name")
        kwargs = {}
        if display_name is not None:
            value = escape_scim_filter_value(display_name)
            kwargs["filter"] = f'displayName eq "{value}"'
        return self.list_all_resources(self.client.list_groups, **kwargs)


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        **OCI_IDENTITY_DOMAIN_ARGS,
        group_id=dict(type="str"),
        display_name=dict(type="str"),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["domain_id", "domain_url"]],
        mutually_exclusive=[["domain_id", "domain_url"]],
    )
    OciGroupInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
