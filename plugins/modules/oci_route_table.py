# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_route_table
short_description: Manage a Route Table resource in Oracle Cloud Infrastructure
description:
  - Create, update, and delete OCI route tables.
  - Uses the shared OCI helper layer for authentication, waiting, retry
    behavior, and result shaping.
  - Create requests must omit C(route_table_id). After create, capture the
    returned route table ID and use it for later C(state=present) and
    C(state=absent) tasks.
  - C(route_rules) is always replaced in full on update. The module does not
    merge individual rules into the existing rule set.
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
      - The desired lifecycle state of the route table.
    type: str
    choices: [present, absent]
    default: present
  route_table_id:
    description:
      - The OCID of the route table.
      - When provided, the module manages this exact route table.
      - Required to distinguish between multiple route tables that share the
        same scoped C(name).
    type: str
  name:
    description:
      - Human-readable name for the route table.
      - Required when creating a route table.
      - When C(route_table_id) is omitted, the module uses
        C(compartment_id + vcn_id + name) to find an existing route table.
      - If exactly one route table matches, C(state=present) manages it as the
        update target and C(state=absent) deletes it.
      - If more than one route table matches, the task fails and the caller
        must supply C(route_table_id).
    type: str
  compartment_id:
    description:
      - The OCID of the compartment containing the route table.
      - Required when creating a route table.
      - Also scopes name-based route table lookups when C(route_table_id) is
        omitted.
    type: str
  vcn_id:
    description:
      - The OCID of the VCN containing the route table.
      - Required when creating a route table.
      - Also scopes name-based route table lookups when C(route_table_id) is
        omitted.
    type: str
  route_rules:
    description:
      - The full set of route rules for the route table.
      - Replaces the entire rule set on update. Omit this to leave existing
        rules untouched.
    type: list
    elements: dict
    suboptions:
      destination:
        description:
          - A destination CIDR block or OCI service C(cidr_block) label,
            depending on C(destination_type).
        type: str
        required: true
      destination_type:
        description:
          - Whether C(destination) is a CIDR block or an OCI service label.
        type: str
        choices: [CIDR_BLOCK, SERVICE_CIDR_BLOCK]
        default: CIDR_BLOCK
      network_entity_id:
        description:
          - The OCID of the target for matching traffic, such as an internet
            gateway, NAT gateway, service gateway, DRG, or private IP.
        type: str
        required: true
      description:
        description:
          - An optional human-readable description of the rule.
        type: str
"""

EXAMPLES = r"""
- name: Create a route table with a route to an internet gateway
  oracle.oci.oci_route_table:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    name: example-route-table
    route_rules:
      - destination: 0.0.0.0/0
        destination_type: CIDR_BLOCK
        network_entity_id: ocid1.internetgateway.oc1..example
  register: created_route_table

- name: Replace the route rules on an existing route table
  oracle.oci.oci_route_table:
    state: present
    route_table_id: "{{ created_route_table.resource.id }}"
    route_rules:
      - destination: 0.0.0.0/0
        network_entity_id: ocid1.natgateway.oc1..example

- name: Delete the created route table
  oracle.oci.oci_route_table:
    state: absent
    route_table_id: "{{ created_route_table.resource.id }}"

- name: Delete a uniquely named route table without providing route_table_id
  oracle.oci.oci_route_table:
    state: absent
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    name: example-route-table
"""

RETURN = r"""
resource:
  description: The route table resource.
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
WAIT_FOR_ROUTE_TABLE_STATES = [LIFECYCLE_AVAILABLE]

ROUTE_RULE_FIELDS = (
    "destination",
    "destination_type",
    "network_entity_id",
    "description",
)


def _normalize_route_rule(route_rule):
    return {field: route_rule.get(field) for field in ROUTE_RULE_FIELDS}


def _normalized_route_rules(route_rules):
    return [_normalize_route_rule(route_rule) for route_rule in (route_rules or [])]


def _route_rules_sort_key(route_rules):
    return sorted(
        tuple(sorted(route_rule.items())) for route_rule in route_rules
    )


def build_route_rule_models(route_rules):
    return [
        oci.core.models.RouteRule(**_normalize_route_rule(route_rule))
        for route_rule in (route_rules or [])
    ]


def build_create_route_table_details(params):
    details = filter_none_values(
        {
            "compartment_id": params.get("compartment_id"),
            "vcn_id": params.get("vcn_id"),
            "display_name": params.get("name"),
            "route_rules": build_route_rule_models(params.get("route_rules")),
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
        }
    )
    return oci.core.models.CreateRouteTableDetails(**details)


class OciRouteTableModule(OciResourceBase):
    """Concrete resource adapter for OCI route tables."""

    @property
    def client_class(self):
        return oci.core.VirtualNetworkClient

    resource_id_param = "route_table_id"
    list_resource_method = "list_route_tables"
    list_filter_params = ("vcn_id",)
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "route table"
    update_field_specs = [
        {
            "param_name": "name",
            "resource_field": "display_name",
            "update_field": "display_name",
            "is_mutable": True,
        },
        {
            "param_name": "route_rules",
            "resource_field": "route_rules",
            "is_mutable": True,
            "strategy": "plan_route_rules_strategy",
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
            self.client.get_route_table,
            rt_id=resource_id,
        )

    def plan_route_rules_strategy(self, resource, resource_dict, spec, desired_value):
        desired_rules = _normalized_route_rules(desired_value)
        current_rules = _normalized_route_rules(resource_dict.get("route_rules"))
        if _route_rules_sort_key(current_rules) == _route_rules_sort_key(desired_rules):
            return []
        return [("replace", desired_rules)]

    def create_resource(self):
        create_route_table_details = build_create_route_table_details(self.module.params)
        response = self.call_with_retry(
            self.client.create_route_table,
            create_route_table_details=create_route_table_details,
        )
        return self.get_mutation_result(
            response.data,
            getattr(response.data, "id", None),
            WAIT_FOR_ROUTE_TABLE_STATES,
        )

    def build_update_details(self, update_model_fields):
        return oci.core.models.UpdateRouteTableDetails(**update_model_fields)

    def update_resource(self, resource):
        update_plan = self.get_update_plan(resource)
        update_model_fields = dict(update_plan["update_model_fields"])

        for strategy_operation in update_plan["strategy_operations"]:
            if strategy_operation["param_name"] != "route_rules":
                continue
            operations = strategy_operation["operations"]
            if operations:
                _, desired_rules = operations[0]
                update_model_fields["route_rules"] = build_route_rule_models(desired_rules)

        if not update_model_fields:
            return resource

        update_details = self.build_update_details(update_model_fields)
        response = self.call_with_retry(
            self.client.update_route_table,
            rt_id=resource.id,
            update_route_table_details=update_details,
        )
        return self.get_mutation_result(
            response.data,
            resource.id,
            WAIT_FOR_ROUTE_TABLE_STATES,
        )

    def delete_resource(self, resource):
        return self.delete_resource_and_wait(
            resource,
            self.client.delete_route_table,
            rt_id=resource.id,
        )


def main():
    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        route_table_id=dict(type="str"),
        vcn_id=dict(type="str"),
        route_rules=dict(
            type="list",
            elements="dict",
            options=dict(
                destination=dict(type="str", required=True),
                destination_type=dict(
                    type="str",
                    choices=["CIDR_BLOCK", "SERVICE_CIDR_BLOCK"],
                    default="CIDR_BLOCK",
                ),
                network_entity_id=dict(type="str", required=True),
                description=dict(type="str"),
            ),
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    OciRouteTableModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
