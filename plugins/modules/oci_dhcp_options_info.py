# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_dhcp_options_info
short_description: Retrieve DHCP Options information from Oracle Cloud Infrastructure
description:
  - Retrieve details about one or more OCI VCN DHCP options sets.
  - Use C(dhcp_options_id) to fetch a single DHCP options set, or
    C(compartment_id) to list DHCP options in a compartment.
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
      - The OCID of the compartment to list DHCP options from.
      - Required when listing resources.
    type: str
  dhcp_options_id:
    description:
      - The OCID of a specific DHCP options set to retrieve.
      - When specified, returns a single resource instead of a list.
    type: str
  vcn_id:
    description:
      - Filter listed DHCP options by VCN.
      - Only used when C(compartment_id) is provided.
    type: str
"""

EXAMPLES = r"""
- name: List all DHCP options in a compartment
  oracle.oci.oci_dhcp_options_info:
    compartment_id: ocid1.compartment.oc1..example

- name: List DHCP options in a VCN by name
  oracle.oci.oci_dhcp_options_info:
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    name: example-dhcp-options

- name: Get a specific DHCP options set
  oracle.oci.oci_dhcp_options_info:
    dhcp_options_id: ocid1.dhcpoptions.oc1..example
"""

RETURN = r"""
dhcp_options:
  description: List of DHCP options sets that matched the query.
  returned: always
  type: list
  elements: dict
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


class OciDhcpOptionsInfoModule(OciInfoBase):
    """Concrete info adapter for OCI VCN DHCP options."""

    @property
    def client_class(self):
        return oci.core.VirtualNetworkClient

    results_key = "dhcp_options"
    resource_id_param = "dhcp_options_id"
    resource_id_kwarg = "dhcp_id"
    resource_get_method = "get_dhcp_options"
    list_resource_method = "list_dhcp_options"
    list_filter_params = [
        "compartment_id",
        "vcn_id",
        "lifecycle_state",
    ]


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        compartment_id=dict(type="str"),
        dhcp_options_id=dict(type="str"),
        vcn_id=dict(type="str"),
        name=dict(type="str"),
        lifecycle_state=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["compartment_id", "dhcp_options_id"]],
    )

    OciDhcpOptionsInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
