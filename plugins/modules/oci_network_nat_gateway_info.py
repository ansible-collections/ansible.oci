# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_network_nat_gateway_info
short_description: Retrieve NAT Gateway information from Oracle Cloud Infrastructure
description:
  - Retrieve details about one or more OCI NAT gateways.
  - Use C(nat_gateway_id) to fetch a single NAT gateway, or C(compartment_id)
    to list NAT gateways in a compartment.
  - This is a read-only module and does not modify resources.
version_added: "1.0.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_info_filter_options
options:
  compartment_id:
    description:
      - The OCID of the compartment to list NAT gateways from.
      - Required when listing resources.
    type: str
  nat_gateway_id:
    description:
      - The OCID of a specific NAT gateway to retrieve.
      - When specified, returns a single resource instead of a list.
    type: str
  vcn_id:
    description:
      - Filter listed NAT gateways by VCN.
      - Only used when C(compartment_id) is provided.
    type: str
"""

EXAMPLES = r"""
- name: List all NAT gateways in a compartment
  ansible.oci.oci_network_nat_gateway_info:
    compartment_id: ocid1.compartment.oc1..example

- name: List NAT gateways in a VCN by name
  ansible.oci.oci_network_nat_gateway_info:
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    name: example-nat-gateway

- name: Get a specific NAT gateway
  ansible.oci.oci_network_nat_gateway_info:
    nat_gateway_id: ocid1.natgateway.oc1..example
"""

RETURN = r"""
nat_gateways:
  description: List of NAT gateways that matched the query.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The OCID of the NAT gateway.
      type: str
      returned: always
      sample: ocid1.natgateway.oc1..example
    name:
      description: The display name of the NAT gateway.
      type: str
      returned: always
      sample: example-nat-gateway
    compartment_id:
      description: The OCID of the compartment containing the NAT gateway.
      type: str
      returned: always
      sample: ocid1.compartment.oc1..example
    vcn_id:
      description: The OCID of the VCN containing the NAT gateway.
      type: str
      returned: always
      sample: ocid1.vcn.oc1..example
    lifecycle_state:
      description: The current lifecycle state of the NAT gateway.
      type: str
      returned: always
      sample: AVAILABLE
    block_traffic:
      description: Whether the NAT gateway blocks outbound internet traffic.
      type: bool
      returned: always
      sample: false
    nat_ip:
      description: The public IP address associated with the NAT gateway.
      type: str
      returned: always
      sample: 192.0.2.1
    public_ip_id:
      description: The OCID of the reserved public IP associated with the NAT gateway, if any.
      type: str
      returned: always
      sample: null
    route_table_id:
      description: The OCID of the route table directly associated with the NAT gateway, if any.
      type: str
      returned: always
      sample: null
    freeform_tags:
      description: Free-form tags applied to the NAT gateway.
      type: dict
      returned: always
      sample: {"environment": "production"}
    defined_tags:
      description: Defined tags applied to the NAT gateway.
      type: dict
      returned: always
      sample: {"Operations": {"CostCenter": "42"}}
    time_created:
      description: The date and time the NAT gateway was created, in RFC3339 format.
      type: str
      returned: always
      sample: "2026-01-01T00:00:00.000Z"
  sample:
    - id: ocid1.natgateway.oc1..example
      name: example-nat-gateway
      compartment_id: ocid1.compartment.oc1..example
      vcn_id: ocid1.vcn.oc1..example
      lifecycle_state: AVAILABLE
      block_traffic: false
      nat_ip: 192.0.2.1
      public_ip_id: null
      route_table_id: null
      freeform_tags: {"environment": "production"}
      defined_tags: {"Operations": {"CostCenter": "42"}}
      time_created: "2026-01-01T00:00:00.000Z"
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


class OciNetworkNatGatewayInfoModule(OciInfoBase):
    """Concrete info adapter for OCI NAT gateways."""

    @property
    def client_class(self):
        return oci.core.VirtualNetworkClient

    results_key = "nat_gateways"
    resource_id_param = "nat_gateway_id"
    resource_get_method = "get_nat_gateway"
    list_resource_method = "list_nat_gateways"
    list_filter_params = [
        "compartment_id",
        "vcn_id",
        "lifecycle_state",
    ]


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        compartment_id=dict(type="str"),
        nat_gateway_id=dict(type="str"),
        vcn_id=dict(type="str"),
        name=dict(type="str"),
        lifecycle_state=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["compartment_id", "nat_gateway_id"]],
    )

    OciNetworkNatGatewayInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
