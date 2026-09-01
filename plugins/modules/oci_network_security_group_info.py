# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_network_security_group_info
short_description: Retrieve Network Security Group information from Oracle Cloud Infrastructure
description:
  - Retrieve one or more OCI Network Security Groups.
  - Use C(network_security_group_id) for a single resource or C(compartment_id)
    to list resources.
  - This module does not return or manage Network Security Group rules.
version_added: "1.0.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_info_filter_options
options:
  compartment_id:
    description:
      - The OCID of the compartment from which to list Network Security Groups.
    type: str
  network_security_group_id:
    description:
      - The OCID of a specific Network Security Group to retrieve.
    type: str
  vcn_id:
    description:
      - Filter listed Network Security Groups by VCN.
    type: str
"""

EXAMPLES = r"""
- name: List Network Security Groups in a compartment
  ansible.oci.oci_network_security_group_info:
    compartment_id: ocid1.compartment.oc1..example

- name: List Network Security Groups in a VCN by name
  ansible.oci.oci_network_security_group_info:
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    name: example-network-security-group

- name: Get a Network Security Group by OCID
  ansible.oci.oci_network_security_group_info:
    network_security_group_id: ocid1.networksecuritygroup.oc1..example
"""

RETURN = r"""
network_security_groups:
  description: Network Security Groups that matched the query.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The OCID of the Network Security Group.
      type: str
      returned: always
    name:
      description: The display name of the Network Security Group.
      type: str
      returned: always
    compartment_id:
      description: The OCID of the containing compartment.
      type: str
      returned: always
    vcn_id:
      description: The OCID of the containing VCN.
      type: str
      returned: always
    lifecycle_state:
      description: The current lifecycle state.
      type: str
      returned: always
    freeform_tags:
      description: Free-form tags applied to the resource.
      type: dict
      returned: always
    defined_tags:
      description: Defined tags applied to the resource.
      type: dict
      returned: always
    time_created:
      description: The date and time the resource was created.
      type: str
      returned: always
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import (
    OciInfoBase,
)

imported_oci_sdk = import_oci_sdk()
oci = imported_oci_sdk[0]
HAS_OCI_SDK = imported_oci_sdk[1]


class OciNetworkSecurityGroupInfoModule(OciInfoBase):
    """Concrete info adapter for OCI Network Security Groups."""

    @property
    def client_class(self):
        return oci.core.VirtualNetworkClient

    results_key = "network_security_groups"
    resource_id_param = "network_security_group_id"
    resource_get_method = "get_network_security_group"
    list_resource_method = "list_network_security_groups"
    list_filter_params = ["compartment_id", "vcn_id", "lifecycle_state"]


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        compartment_id=dict(type="str"),
        network_security_group_id=dict(type="str"),
        vcn_id=dict(type="str"),
        name=dict(type="str"),
        lifecycle_state=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["compartment_id", "network_security_group_id"]],
    )

    OciNetworkSecurityGroupInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
