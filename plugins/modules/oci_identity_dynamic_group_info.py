# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_identity_dynamic_group_info
short_description: Retrieve dynamic groups from an OCI IAM identity domain
description:
  - Gets a dynamic group by its System for Cross-domain Identity Management (SCIM) identifier.
  - Lists dynamic groups through the OCI IAM Identity Domains API.
version_added: "1.2.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  domain_id:
    description:
      - OCID of the identity domain.
      - Set exactly one of C(domain_id) or C(domain_url).
    type: str
  domain_url:
    description:
      - Service endpoint of the identity domain.
      - Set exactly one of C(domain_id) or C(domain_url).
    type: str
  dynamic_group_id:
    description: SCIM identifier of a specific dynamic group.
    type: str
  name:
    description: Exact display-name filter.
    type: str
"""

EXAMPLES = r"""
- name: List dynamic groups by display name
  ansible.oci.oci_identity_dynamic_group_info:
    domain_id: ocid1.domain.oc1..example
    name: compute-instances

- name: Get one dynamic group
  ansible.oci.oci_identity_dynamic_group_info:
    domain_url: https://idcs-example.identity.oraclecloud.com
    dynamic_group_id: 0123456789abcdef
"""

RETURN = r"""
dynamic_groups:
  description: Dynamic groups that match the query.
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
      description: OCID of the identity domain containing the dynamic group.
      type: str
    name:
      description: Display name.
      type: str
    description:
      description: Description of the dynamic group.
      type: str
    matching_rule:
      description: Matching rule of the dynamic group.
      type: str
    freeform_tags:
      description: Freeform tags on the dynamic group.
      type: dict
    defined_tags:
      description: Defined tags on the dynamic group, including tags applied by OCI.
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
    OciIdentityDomainInfoBase,
    serialize_dynamic_group,
)


class OciIdentityDynamicGroupInfoModule(OciIdentityDomainInfoBase):
    """Retrieve Identity Domains dynamic groups."""

    results_key = "dynamic_groups"
    resource_id_param = "dynamic_group_id"
    resource_id_kwarg = "dynamic_resource_group_id"
    resource_get_method = "get_dynamic_resource_group"
    list_resource_method = "list_dynamic_resource_groups"
    scim_response_attributes = ("matchingRule",)

    def serialize_result_resource(self, resource):
        """Serialize a dynamic group for module output.

        The inherited serializer does not normalize SCIM tags and metadata.

        Args:
            resource: Identity Domains dynamic group model.

        Returns:
            A dictionary of dynamic group fields.
        """
        return serialize_dynamic_group(resource)


def main():
    """Run the dynamic group info module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        **OCI_IDENTITY_DOMAIN_ARGS,
        dynamic_group_id=dict(type="str"),
        name=dict(type="str"),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["domain_id", "domain_url"]],
        mutually_exclusive=[["domain_id", "domain_url"]],
    )
    OciIdentityDynamicGroupInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
