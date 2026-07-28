# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_network_vcn_info
short_description: Retrieve Virtual Cloud Network information from Oracle Cloud Infrastructure
description:
  - Retrieve details about one or more OCI Virtual Cloud Networks (VCNs).
  - Use C(vcn_id) to fetch a single VCN, or C(compartment_id) to list VCNs in a compartment.
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
      - The OCID of the compartment to list VCNs from.
      - Required when listing resources.
    type: str
  vcn_id:
    description:
      - The OCID of a specific VCN to retrieve.
      - When specified, returns a single resource instead of a list.
    type: str
"""

EXAMPLES = r"""
- name: List all VCNs in a compartment
  oracle.oci.oci_network_vcn_info:
    compartment_id: ocid1.compartment.oc1..example

- name: List VCNs in a compartment by name
  oracle.oci.oci_network_vcn_info:
    compartment_id: ocid1.compartment.oc1..example
    name: example-vcn

- name: Get a specific VCN
  oracle.oci.oci_network_vcn_info:
    vcn_id: ocid1.vcn.oc1..example
"""

RETURN = r"""
vcns:
  description: List of VCNs that matched the query.
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

oci, HAS_OCI_SDK = import_oci_sdk()


class OciNetworkVcnInfoModule(OciInfoBase):
    """Concrete info adapter for OCI VCNs."""

    @property
    def client_class(self):
        return oci.core.VirtualNetworkClient

    results_key = "vcns"
    resource_id_param = "vcn_id"
    resource_get_method = "get_vcn"
    list_resource_method = "list_vcns"
    list_filter_params = ("compartment_id", "lifecycle_state")


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        compartment_id=dict(type="str"),
        vcn_id=dict(type="str"),
        name=dict(type="str"),
        lifecycle_state=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[("compartment_id", "vcn_id")],
    )

    OciNetworkVcnInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
