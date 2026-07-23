# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_subnet_info
short_description: Retrieve Subnet information from Oracle Cloud Infrastructure
description:
  - Retrieve details about one or more OCI subnets.
  - Use C(subnet_id) to fetch a single subnet, or C(compartment_id) to list
    subnets in a compartment.
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
      - The OCID of the compartment to list subnets from.
      - Required when listing resources.
    type: str
  subnet_id:
    description:
      - The OCID of a specific subnet to retrieve.
      - When specified, returns a single resource instead of a list.
    type: str
  vcn_id:
    description:
      - Filter listed subnets by VCN.
      - Only used when C(compartment_id) is provided.
    type: str
"""

EXAMPLES = r"""
- name: List all subnets in a compartment
  oracle.oci.oci_subnet_info:
    compartment_id: ocid1.compartment.oc1..example

- name: List subnets in a VCN by display name
  oracle.oci.oci_subnet_info:
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    display_name: example-subnet

- name: Get a specific subnet
  oracle.oci.oci_subnet_info:
    subnet_id: ocid1.subnet.oc1..example
"""

RETURN = r"""
subnets:
  description: List of subnets that matched the query.
  returned: always
  type: list
  elements: dict
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.oracle.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
)
from ansible_collections.oracle.oci.plugins.module_utils.oci_info import (
    OciInfoBase,
)

try:
    import oci

    HAS_OCI_SDK = True
except ImportError:
    HAS_OCI_SDK = False
    oci = None


class OciSubnetInfoModule(OciInfoBase):
    """Concrete info adapter for OCI subnets."""

    client_class = oci.core.VirtualNetworkClient if HAS_OCI_SDK else object()
    results_key = "subnets"
    resource_id_param = "subnet_id"
    resource_get_method = "get_subnet"
    list_resource_method = "list_subnets"
    list_filter_params = (
        "compartment_id",
        "vcn_id",
        "display_name",
        "lifecycle_state",
    )
    known_field_names = ("display_name",)


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        compartment_id=dict(type="str"),
        subnet_id=dict(type="str"),
        vcn_id=dict(type="str"),
        display_name=dict(type="str"),
        lifecycle_state=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[("compartment_id", "subnet_id")],
    )

    OciSubnetInfoModule(module).run()


if __name__ == "__main__":
    main()
