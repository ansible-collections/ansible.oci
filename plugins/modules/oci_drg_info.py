# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_drg_info
short_description: Retrieve Dynamic Routing Gateway (DRG) information from Oracle Cloud Infrastructure
description:
  - Retrieve details about one or more OCI Dynamic Routing Gateways (DRGs).
  - Use C(drg_id) to fetch a single DRG, or C(compartment_id) to list DRGs in
    a compartment.
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
      - The OCID of the compartment to list DRGs from.
      - Required when listing resources.
    type: str
  drg_id:
    description:
      - The OCID of a specific DRG to retrieve.
      - When specified, returns a single resource instead of a list.
    type: str
"""

EXAMPLES = r"""
- name: List all DRGs in a compartment
  oracle.oci.oci_drg_info:
    compartment_id: ocid1.compartment.oc1..example

- name: List DRGs in a compartment by name
  oracle.oci.oci_drg_info:
    compartment_id: ocid1.compartment.oc1..example
    name: example-drg

- name: Get a specific DRG
  oracle.oci.oci_drg_info:
    drg_id: ocid1.drg.oc1..example
"""

RETURN = r"""
drgs:
  description: List of DRGs that matched the query.
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


class OciDrgInfoModule(OciInfoBase):
    """Concrete info adapter for OCI DRGs."""

    @property
    def client_class(self):
        return oci.core.VirtualNetworkClient

    results_key = "drgs"
    resource_id_param = "drg_id"
    resource_get_method = "get_drg"
    list_resource_method = "list_drgs"
    list_filter_params = [
        "compartment_id",
        "lifecycle_state",
    ]


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        compartment_id=dict(type="str"),
        drg_id=dict(type="str"),
        name=dict(type="str"),
        lifecycle_state=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["compartment_id", "drg_id"]],
    )

    OciDrgInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
