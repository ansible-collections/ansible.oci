# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_route_table_info
short_description: Retrieve Route Table information from Oracle Cloud Infrastructure
description:
  - Retrieve details about one or more OCI route tables.
  - Use C(route_table_id) to fetch a single route table, or C(compartment_id)
    to list route tables in a compartment.
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
      - The OCID of the compartment to list route tables from.
      - Required when listing resources.
    type: str
  route_table_id:
    description:
      - The OCID of a specific route table to retrieve.
      - When specified, returns a single resource instead of a list.
    type: str
  vcn_id:
    description:
      - Filter listed route tables by VCN.
      - Only used when C(compartment_id) is provided.
    type: str
"""

EXAMPLES = r"""
- name: List all route tables in a compartment
  oracle.oci.oci_route_table_info:
    compartment_id: ocid1.compartment.oc1..example

- name: List route tables in a VCN by name
  oracle.oci.oci_route_table_info:
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    name: example-route-table

- name: Get a specific route table
  oracle.oci.oci_route_table_info:
    route_table_id: ocid1.routetable.oc1..example
"""

RETURN = r"""
route_tables:
  description: List of route tables that matched the query.
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


class OciRouteTableInfoModule(OciInfoBase):
    """Concrete info adapter for OCI route tables."""

    @property
    def client_class(self):
        return oci.core.VirtualNetworkClient

    results_key = "route_tables"
    resource_id_param = "route_table_id"
    resource_id_kwarg = "rt_id"
    resource_get_method = "get_route_table"
    list_resource_method = "list_route_tables"
    list_filter_params = [
        "compartment_id",
        "vcn_id",
        "lifecycle_state",
    ]


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        compartment_id=dict(type="str"),
        route_table_id=dict(type="str"),
        vcn_id=dict(type="str"),
        name=dict(type="str"),
        lifecycle_state=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["compartment_id", "route_table_id"]],
    )

    OciRouteTableInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
