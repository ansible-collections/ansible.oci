# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_local_peering_gateway
short_description: Manage a Local Peering Gateway resource in Oracle Cloud Infrastructure
description:
  - Create, update, and delete OCI local peering gateways (LPGs).
  - Uses the shared OCI helper layer for authentication, waiting, retry
    behavior, and result shaping.
  - Create requests must omit C(local_peering_gateway_id). After create,
    capture the returned LPG ID and use it for later C(state=present) and
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
      - The desired lifecycle state of the local peering gateway.
    type: str
    choices: [present, absent]
    default: present
  local_peering_gateway_id:
    description:
      - The OCID of the local peering gateway.
      - When provided, the module manages this exact local peering gateway.
      - Required to distinguish between multiple local peering gateways that
        share the same scoped C(name).
    type: str
  name:
    description:
      - Human-readable name for the local peering gateway.
      - Required when creating a local peering gateway.
      - When C(local_peering_gateway_id) is omitted, the module uses
        C(compartment_id + vcn_id + name) to find an existing local peering
        gateway.
      - If exactly one local peering gateway matches, C(state=present)
        manages it as the update target and C(state=absent) deletes it.
      - If more than one local peering gateway matches, the task fails and
        the caller must supply C(local_peering_gateway_id).
    type: str
  compartment_id:
    description:
      - The OCID of the compartment containing the local peering gateway.
      - Required when creating a local peering gateway.
      - The module does not move an existing local peering gateway to
        another compartment.
      - Also scopes name-based local peering gateway lookups when
        C(local_peering_gateway_id) is omitted.
    type: str
  vcn_id:
    description:
      - The OCID of the VCN containing the local peering gateway.
      - Required when creating a local peering gateway.
      - The module does not support moving an existing local peering gateway
        to another VCN.
      - Also scopes name-based local peering gateway lookups when
        C(local_peering_gateway_id) is omitted.
    type: str
  route_table_id:
    description:
      - The OCID of a route table to associate directly with the local
        peering gateway, for OCI's transit routing feature. This controls
        how traffic arriving through this gateway is routed once it enters
        the VCN, separately from the route table assigned to any subnet.
      - This is an optional, advanced setting. Most deployments do not need
        it and can omit it; only set it if you are implementing transit
        routing. Omitting it leaves traffic subject to each subnet's own
        route table as usual.
      - Because a route table's own rules may need to reference this
        gateway's OCID (see C(network_entity_id) on
        C(oracle.oci.oci_route_table)), create the gateway first without
        C(route_table_id), create the route table referencing the gateway,
        then update the gateway with C(route_table_id) if transit routing is
        required.
    type: str
  peer_id:
    description:
      - The OCID of the other local peering gateway to peer with.
      - This is not a fixed or well-known value. Like C(network_entity_id)
        on C(oracle.oci.oci_route_table), it is the OCID OCI assigns to the
        other LPG when it is created, so both local peering gateways must
        already exist before you can peer them. Peering is typically
        initiated from one side only; setting C(peer_id) here establishes
        the peering connection with the LPG identified by that OCID.
      - The two LPGs being peered must belong to different VCNs. Peering two
        LPGs in the same VCN, or the same LPG to itself, is rejected by OCI.
      - This module can establish or change a peering connection but cannot
        break one; omit this parameter to leave an existing peering
        connection untouched rather than to remove it.
    type: str
"""

EXAMPLES = r"""
- name: Create a local peering gateway with only the required parameters
  oracle.oci.oci_local_peering_gateway:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    name: example-lpg
  register: created_lpg

- name: Create a second local peering gateway in a different VCN to peer with
  oracle.oci.oci_local_peering_gateway:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: ocid1.vcn.oc1..other-example
    name: example-lpg-peer
  register: created_lpg_peer

- name: Peer the two local peering gateways
  oracle.oci.oci_local_peering_gateway:
    state: present
    local_peering_gateway_id: "{{ created_lpg.resource.id }}"
    peer_id: "{{ created_lpg_peer.resource.id }}"

- name: Reconcile a uniquely named local peering gateway by name
  oracle.oci.oci_local_peering_gateway:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    name: example-lpg
    route_table_id: ocid1.routetable.oc1..example

- name: Delete the created local peering gateway
  oracle.oci.oci_local_peering_gateway:
    state: absent
    local_peering_gateway_id: "{{ created_lpg.resource.id }}"

- name: Delete a uniquely named local peering gateway without providing local_peering_gateway_id
  oracle.oci.oci_local_peering_gateway:
    state: absent
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    name: example-lpg
"""

RETURN = r"""
resource:
  description: The local peering gateway resource.
  returned: when state != absent
  type: dict
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
WAIT_FOR_LPG_STATES = [LIFECYCLE_AVAILABLE]


def build_create_local_peering_gateway_details(params):
    details = filter_none_values(
        {
            "compartment_id": params.get("compartment_id"),
            "vcn_id": params.get("vcn_id"),
            "display_name": params.get("name"),
            "route_table_id": params.get("route_table_id"),
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
        }
    )
    return oci.core.models.CreateLocalPeeringGatewayDetails(**details)


class OciLocalPeeringGatewayModule(OciResourceBase):
    """Concrete resource adapter for OCI local peering gateways."""

    @property
    def client_class(self):
        return oci.core.VirtualNetworkClient

    resource_id_param = "local_peering_gateway_id"
    list_resource_method = "list_local_peering_gateways"
    list_filter_params = ("vcn_id",)
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "local peering gateway"
    update_wait_states = WAIT_FOR_LPG_STATES
    update_field_specs = [
        {
            "param_name": "name",
            "resource_field": "display_name",
            "update_field": "display_name",
            "is_mutable": True,
        },
        {
            "param_name": "route_table_id",
            "resource_field": "route_table_id",
            "update_field": "route_table_id",
            "is_mutable": True,
        },
        {
            "param_name": "peer_id",
            "is_mutable": True,
            "strategy": "plan_peer_id_strategy",
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
            self.client.get_local_peering_gateway,
            local_peering_gateway_id=resource_id,
        )

    def plan_peer_id_strategy(self, resource, resource_dict, spec, desired_value):
        if resource_dict.get("peer_id") == desired_value:
            return []
        return [("connect", desired_value)]

    def create_resource(self):
        create_details = build_create_local_peering_gateway_details(self.module.params)
        response = self.call_with_retry(
            self.client.create_local_peering_gateway,
            create_local_peering_gateway_details=create_details,
        )
        return self.get_mutation_result(
            response.data,
            getattr(response.data, "id", None),
            WAIT_FOR_LPG_STATES,
        )

    def build_update_details(self, update_model_fields):
        return oci.core.models.UpdateLocalPeeringGatewayDetails(**update_model_fields)

    def update_resource(self, resource):
        update_plan = self.get_update_plan(resource)
        current_resource = resource

        for strategy_operation in update_plan["strategy_operations"]:
            if strategy_operation["param_name"] != "peer_id":
                continue
            operations = strategy_operation["operations"]
            if not operations:
                continue
            desired_peer_id = operations[0][1]
            self.call_with_retry(
                self.client.connect_local_peering_gateways,
                local_peering_gateway_id=resource.id,
                connect_local_peering_gateways_details=(
                    oci.core.models.ConnectLocalPeeringGatewaysDetails(
                        peer_id=desired_peer_id
                    )
                ),
            )
            current_resource = self.wait_for_resource_id(resource.id, WAIT_FOR_LPG_STATES)
            update_plan = self.get_update_plan(current_resource)

        update_model_fields = dict(update_plan["update_model_fields"])
        if not update_model_fields:
            return current_resource

        update_details = self.build_update_details(update_model_fields)
        response = self.call_with_retry(
            self.client.update_local_peering_gateway,
            local_peering_gateway_id=current_resource.id,
            update_local_peering_gateway_details=update_details,
        )
        return self.get_mutation_result(
            response.data,
            current_resource.id,
            WAIT_FOR_LPG_STATES,
        )

    def delete_resource(self, resource):
        return self.delete_resource_and_wait(
            resource,
            self.client.delete_local_peering_gateway,
            local_peering_gateway_id=resource.id,
        )


def main():
    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        local_peering_gateway_id=dict(type="str"),
        vcn_id=dict(type="str"),
        route_table_id=dict(type="str"),
        peer_id=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    OciLocalPeeringGatewayModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
