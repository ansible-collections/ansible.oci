# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_security_list_info
short_description: Retrieve Security List information from Oracle Cloud Infrastructure
description:
  - Retrieve details about one or more OCI security lists.
  - Use C(security_list_id) to fetch a single security list, or
    C(compartment_id) to list security lists in a compartment.
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
      - The OCID of the compartment to list security lists from.
      - Required when listing resources.
    type: str
  security_list_id:
    description:
      - The OCID of a specific security list to retrieve.
      - When specified, returns a single resource instead of a list.
    type: str
  vcn_id:
    description:
      - Filter listed security lists by VCN.
      - Only used when C(compartment_id) is provided.
    type: str
"""

EXAMPLES = r"""
- name: List all security lists in a compartment
  oracle.oci.oci_security_list_info:
    compartment_id: ocid1.compartment.oc1..example

- name: List security lists in a VCN by name
  oracle.oci.oci_security_list_info:
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    name: example-security-list

- name: Get a specific security list
  oracle.oci.oci_security_list_info:
    security_list_id: ocid1.securitylist.oc1..example
"""

RETURN = r"""
security_lists:
  description: List of security lists that matched the query.
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


class OciSecurityListInfoModule(OciInfoBase):
    """Concrete info adapter for OCI security lists."""

    @property
    def client_class(self):
        return oci.core.VirtualNetworkClient

    results_key = "security_lists"
    resource_id_param = "security_list_id"
    resource_get_method = "get_security_list"
    list_resource_method = "list_security_lists"
    list_filter_params = [
        "compartment_id",
        "vcn_id",
        "lifecycle_state",
    ]


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        compartment_id=dict(type="str"),
        security_list_id=dict(type="str"),
        vcn_id=dict(type="str"),
        name=dict(type="str"),
        lifecycle_state=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["compartment_id", "security_list_id"]],
    )

    OciSecurityListInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
