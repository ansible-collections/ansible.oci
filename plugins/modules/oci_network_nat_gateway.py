# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_network_nat_gateway
short_description: Manage a NAT Gateway resource in Oracle Cloud Infrastructure
description:
  - Create, update, and delete OCI NAT gateways.
  - Uses the shared OCI helper layer for authentication, waiting, retry
    behavior, and result shaping.
  - Create requests must omit C(nat_gateway_id). After create, capture the
    returned NAT gateway ID and use it for later C(state=present) and
    C(state=absent) tasks.
version_added: "1.0.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - oracle.oci.oci_auth_options
  - oracle.oci.oci_name_lookup_options
  - oracle.oci.oci_wait_options
  - oracle.oci.oci_tags_options
options:
  state:
    description:
      - The desired lifecycle state of the NAT gateway.
    type: str
    choices: [present, absent]
    default: present
  nat_gateway_id:
    description:
      - The OCID of the NAT gateway.
      - When provided, the module manages this exact NAT gateway.
      - Required to distinguish between multiple NAT gateways that share the
        same scoped C(name).
    type: str
  name:
    description:
      - Human-readable name for the NAT gateway.
      - Required when creating a NAT gateway.
      - When C(nat_gateway_id) is omitted, the module uses
        C(compartment_id + vcn_id + name) to find an existing NAT gateway.
      - If exactly one NAT gateway matches, C(state=present) manages it as the
        update target and C(state=absent) deletes it.
      - If more than one NAT gateway matches, the task fails and the caller
        must supply C(nat_gateway_id).
    type: str
  compartment_id:
    description:
      - The OCID of the compartment containing the NAT gateway.
      - Required when creating a NAT gateway.
      - The module does not move an existing NAT gateway to another
        compartment.
      - Also scopes name-based NAT gateway lookups when C(nat_gateway_id) is
        omitted.
    type: str
  vcn_id:
    description:
      - The OCID of the VCN containing the NAT gateway.
      - Required when creating a NAT gateway.
      - The module does not support moving an existing NAT gateway to another
        VCN.
      - Also scopes name-based NAT gateway lookups when C(nat_gateway_id) is
        omitted.
    type: str
  block_traffic:
    description:
      - Whether the NAT gateway blocks outbound internet traffic.
    type: bool
  route_table_id:
    description:
      - The OCID of a route table to associate directly with the NAT
        gateway, for OCI's transit routing feature. This controls how
        traffic arriving through this gateway is routed once it enters the
        VCN, separately from the route table assigned to any subnet.
      - This is an optional, advanced setting. Most deployments do not need
        it and can omit it; only set it if you are implementing transit
        routing. Omitting it leaves traffic subject to each subnet's own
        route table as usual.
      - Because a route table's own rules may need to reference this
        gateway's OCID (see C(network_entity_id) on
        C(oracle.oci.oci_network_route_table)), create the gateway first without
        C(route_table_id), create the route table referencing the gateway,
        then update the gateway with C(route_table_id) if transit routing is
        required. See the examples below.
    type: str
  public_ip_id:
    description:
      - The OCID of the reserved public IP address to associate with the NAT
        gateway.
      - The OCI API treats this as create-time only.
      - When omitted at create time, OCI assigns an ephemeral public IP.
    type: str
"""

EXAMPLES = r"""
- name: Create a NAT gateway with only the required parameters
  oracle.oci.oci_network_nat_gateway:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    name: example-nat-gateway
  register: created_nat_gateway

- name: Create a route table with a rule pointing at that NAT gateway
  oracle.oci.oci_network_route_table:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    name: example-route-table
    route_rules:
      - destination: 0.0.0.0/0
        network_entity_id: "{{ created_nat_gateway.resource.id }}"
  register: created_route_table

- name: Enable transit routing by pointing the gateway back at that route table
  oracle.oci.oci_network_nat_gateway:
    state: present
    nat_gateway_id: "{{ created_nat_gateway.resource.id }}"
    route_table_id: "{{ created_route_table.resource.id }}"

- name: Reconcile a uniquely named NAT gateway by name
  oracle.oci.oci_network_nat_gateway:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    name: example-nat-gateway
    block_traffic: true

- name: Delete the created NAT gateway
  oracle.oci.oci_network_nat_gateway:
    state: absent
    nat_gateway_id: "{{ created_nat_gateway.resource.id }}"

- name: Delete a uniquely named NAT gateway without providing nat_gateway_id
  oracle.oci.oci_network_nat_gateway:
    state: absent
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    name: example-nat-gateway
"""

RETURN = r"""
resource:
  description: The NAT gateway resource.
  returned: when state != absent
  type: dict
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
    id: ocid1.natgateway.oc1..example
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

from ansible_collections.oracle.oci.plugins.module_utils.oci_common import (
    LIFECYCLE_AVAILABLE,
    OCI_COMMON_ARGS,
    filter_none_values,
    import_oci_sdk,
)
from ansible_collections.oracle.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
)

imported_oci_sdk = import_oci_sdk()
oci = imported_oci_sdk[0]
HAS_OCI_SDK = imported_oci_sdk[1]

CREATE_REQUIRED_FIELDS = [
    "compartment_id",
    "vcn_id",
    "name",
]
WAIT_FOR_NAT_GATEWAY_STATES = [LIFECYCLE_AVAILABLE]


def build_create_nat_gateway_details(params):
    details = filter_none_values(
        {
            "compartment_id": params.get("compartment_id"),
            "vcn_id": params.get("vcn_id"),
            "display_name": params.get("name"),
            "block_traffic": params.get("block_traffic"),
            "route_table_id": params.get("route_table_id"),
            "public_ip_id": params.get("public_ip_id"),
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
        }
    )
    return oci.core.models.CreateNatGatewayDetails(**details)


class OciNetworkNatGatewayModule(OciResourceBase):
    """Concrete resource adapter for OCI NAT gateways."""

    @property
    def client_class(self):
        return oci.core.VirtualNetworkClient

    resource_id_param = "nat_gateway_id"
    list_resource_method = "list_nat_gateways"
    list_filter_params = ("vcn_id",)
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "NAT gateway"
    update_method_name = "update_nat_gateway"
    update_details_name = "update_nat_gateway_details"
    update_wait_states = WAIT_FOR_NAT_GATEWAY_STATES
    update_field_specs = [
        {
            "param_name": "name",
            "resource_field": "display_name",
            "update_field": "display_name",
            "is_mutable": True,
        },
        {
            "param_name": "block_traffic",
            "resource_field": "block_traffic",
            "update_field": "block_traffic",
            "is_mutable": True,
        },
        {
            "param_name": "route_table_id",
            "resource_field": "route_table_id",
            "update_field": "route_table_id",
            "is_mutable": True,
        },
        {
            "param_name": "public_ip_id",
            "resource_field": "public_ip_id",
            "is_mutable": False,
            "immutable_reason": "OCI treats public_ip_id as immutable after create",
        },
        {
            "param_name": "vcn_id",
            "resource_field": "vcn_id",
            "is_mutable": False,
        },
        {
            "param_name": "compartment_id",
            "resource_field": "compartment_id",
            "is_mutable": False,
        },
    ]

    def get_resource_response(self, resource_id):
        return self.call_with_retry(
            self.client.get_nat_gateway,
            nat_gateway_id=resource_id,
        )

    def create_resource(self):
        create_nat_gateway_details = build_create_nat_gateway_details(self.module.params)
        response = self.call_with_retry(
            self.client.create_nat_gateway,
            create_nat_gateway_details=create_nat_gateway_details,
        )
        return self.get_mutation_result(
            response.data,
            getattr(response.data, "id", None),
            WAIT_FOR_NAT_GATEWAY_STATES,
        )

    def build_update_details(self, update_model_fields):
        return oci.core.models.UpdateNatGatewayDetails(**update_model_fields)

    def delete_resource(self, resource):
        return self.delete_resource_and_wait(
            resource,
            self.client.delete_nat_gateway,
            nat_gateway_id=resource.id,
        )


def main():
    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        nat_gateway_id=dict(type="str"),
        vcn_id=dict(type="str"),
        block_traffic=dict(type="bool"),
        route_table_id=dict(type="str"),
        public_ip_id=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    OciNetworkNatGatewayModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
