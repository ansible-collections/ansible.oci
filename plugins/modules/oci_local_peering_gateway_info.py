# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_local_peering_gateway_info
short_description: Retrieve Local Peering Gateway information from Oracle Cloud Infrastructure
description:
  - Retrieve details about one or more OCI local peering gateways.
  - Use C(local_peering_gateway_id) to fetch a single local peering gateway,
    or C(compartment_id) to list local peering gateways in a compartment.
  - This is a read-only module and does not modify resources.
version_added: "1.0.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - oracle.oci.oci_auth_options
options:
  compartment_id:
    description:
      - The OCID of the compartment to list local peering gateways from.
      - Required when listing resources.
    type: str
  local_peering_gateway_id:
    description:
      - The OCID of a specific local peering gateway to retrieve.
      - When specified, returns a single resource instead of a list.
    type: str
  vcn_id:
    description:
      - Filter listed local peering gateways by VCN.
      - Only used when C(compartment_id) is provided.
    type: str
  name:
    description:
      - Filter listed local peering gateways by name.
      - Only used when C(compartment_id) is provided.
    type: str
"""

EXAMPLES = r"""
- name: List all local peering gateways in a compartment
  oracle.oci.oci_local_peering_gateway_info:
    compartment_id: ocid1.compartment.oc1..example

- name: List local peering gateways in a VCN by name
  oracle.oci.oci_local_peering_gateway_info:
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    name: example-lpg

- name: Get a specific local peering gateway
  oracle.oci.oci_local_peering_gateway_info:
    local_peering_gateway_id: ocid1.localpeeringgateway.oc1..example
"""

RETURN = r"""
local_peering_gateways:
  description: List of local peering gateways that matched the query.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The OCID of the local peering gateway.
      type: str
      returned: always
      sample: ocid1.localpeeringgateway.oc1..example
    name:
      description: The display name of the local peering gateway.
      type: str
      returned: always
      sample: example-lpg
    compartment_id:
      description: The OCID of the compartment containing the local peering gateway.
      type: str
      returned: always
      sample: ocid1.compartment.oc1..example
    vcn_id:
      description: The OCID of the VCN containing the local peering gateway.
      type: str
      returned: always
      sample: ocid1.vcn.oc1..example
    lifecycle_state:
      description: The current lifecycle state of the local peering gateway.
      type: str
      returned: always
      sample: AVAILABLE
    peer_id:
      description: The OCID of the peered local peering gateway, if peering has been established.
      type: str
      returned: always
      sample: ocid1.localpeeringgateway.oc1..peer-example
    peering_status:
      description: The status of the peering connection, as reported by OCI.
      type: str
      returned: always
      sample: PEERED
    route_table_id:
      description: The OCID of the route table directly associated with the local peering gateway, if any.
      type: str
      returned: always
      sample: null
    freeform_tags:
      description: Free-form tags applied to the local peering gateway.
      type: dict
      returned: always
      sample: {"environment": "production"}
    defined_tags:
      description: Defined tags applied to the local peering gateway.
      type: dict
      returned: always
      sample: {"Operations": {"CostCenter": "42"}}
    time_created:
      description: The date and time the local peering gateway was created, in RFC3339 format.
      type: str
      returned: always
      sample: "2026-01-01T00:00:00.000Z"
  sample:
    - id: ocid1.localpeeringgateway.oc1..example
      name: example-lpg
      compartment_id: ocid1.compartment.oc1..example
      vcn_id: ocid1.vcn.oc1..example
      lifecycle_state: AVAILABLE
      peer_id: ocid1.localpeeringgateway.oc1..peer-example
      peering_status: PEERED
      route_table_id: null
      freeform_tags: {"environment": "production"}
      defined_tags: {"Operations": {"CostCenter": "42"}}
      time_created: "2026-01-01T00:00:00.000Z"
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


class OciLocalPeeringGatewayInfoModule(OciInfoBase):
    """Concrete info adapter for OCI local peering gateways."""

    @property
    def client_class(self):
        return oci.core.VirtualNetworkClient

    results_key = "local_peering_gateways"
    resource_id_param = "local_peering_gateway_id"
    resource_get_method = "get_local_peering_gateway"
    list_resource_method = "list_local_peering_gateways"
    list_filter_params = [
        "compartment_id",
        "vcn_id",
    ]


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        compartment_id=dict(type="str"),
        local_peering_gateway_id=dict(type="str"),
        vcn_id=dict(type="str"),
        name=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["compartment_id", "local_peering_gateway_id"]],
    )

    OciLocalPeeringGatewayInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
