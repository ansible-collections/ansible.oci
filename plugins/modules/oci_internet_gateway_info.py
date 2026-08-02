# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_internet_gateway_info
short_description: Retrieve Internet Gateway information from Oracle Cloud Infrastructure
description:
  - Retrieve details about one or more OCI internet gateways.
  - Use C(internet_gateway_id) to fetch a single internet gateway, or
    C(compartment_id) to list internet gateways in a compartment.
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
      - The OCID of the compartment to list internet gateways from.
      - Required when listing resources.
    type: str
  internet_gateway_id:
    description:
      - The OCID of a specific internet gateway to retrieve.
      - When specified, returns a single resource instead of a list.
    type: str
  vcn_id:
    description:
      - Filter listed internet gateways by VCN.
      - Only used when C(compartment_id) is provided.
    type: str
"""

EXAMPLES = r"""
- name: List all internet gateways in a compartment
  oracle.oci.oci_internet_gateway_info:
    compartment_id: ocid1.compartment.oc1..example

- name: List internet gateways in a VCN by name
  oracle.oci.oci_internet_gateway_info:
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    name: example-internet-gateway

- name: Get a specific internet gateway
  oracle.oci.oci_internet_gateway_info:
    internet_gateway_id: ocid1.internetgateway.oc1..example
"""

RETURN = r"""
internet_gateways:
  description: List of internet gateways that matched the query.
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


class OciInternetGatewayInfoModule(OciInfoBase):
    """Concrete info adapter for OCI internet gateways.

    The OCI SDK getter ``get_internet_gateway`` takes ``ig_id``, not
    ``internet_gateway_id``. ``OciInfoBase`` supports this split through the
    dedicated ``resource_id_kwarg`` attribute: ``resource_id_param`` stays the
    ansible-facing parameter name while ``resource_id_kwarg`` names the actual
    SDK keyword argument.
    """

    @property
    def client_class(self):
        return oci.core.VirtualNetworkClient

    results_key = "internet_gateways"
    resource_id_param = "internet_gateway_id"
    resource_id_kwarg = "ig_id"
    resource_get_method = "get_internet_gateway"
    list_resource_method = "list_internet_gateways"
    list_filter_params = [
        "compartment_id",
        "vcn_id",
        "lifecycle_state",
    ]


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        compartment_id=dict(type="str"),
        internet_gateway_id=dict(type="str"),
        vcn_id=dict(type="str"),
        name=dict(type="str"),
        lifecycle_state=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["compartment_id", "internet_gateway_id"]],
    )

    OciInternetGatewayInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
