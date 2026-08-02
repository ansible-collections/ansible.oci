# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_service_gateway
short_description: Manage a Service Gateway resource in Oracle Cloud Infrastructure
description:
  - Create, update, and delete OCI VCN service gateways.
  - Uses the shared OCI helper layer for authentication, waiting, retry
    behavior, and result shaping.
  - Create requests must omit C(service_gateway_id). After create, capture the
    returned service gateway ID and use it for later C(state=present) and
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
      - The desired lifecycle state of the service gateway.
    type: str
    choices: [present, absent]
    default: present
  service_gateway_id:
    description:
      - The OCID of the service gateway.
      - When provided, the module manages this exact service gateway.
      - Required to distinguish between multiple service gateways that share
        the same scoped C(name).
    type: str
  name:
    description:
      - Human-readable name for the service gateway.
      - Required when creating a service gateway.
      - When C(service_gateway_id) is omitted, the module uses
        C(compartment_id + vcn_id + name) to find an existing service gateway.
      - If exactly one service gateway matches, C(state=present) manages it as
        the update target and C(state=absent) deletes it.
      - If more than one service gateway matches, the task fails and the
        caller must supply C(service_gateway_id).
    type: str
  compartment_id:
    description:
      - The OCID of the compartment containing the service gateway.
      - Required when creating a service gateway.
      - The module does not move an existing service gateway to another
        compartment.
      - Also scopes name-based service gateway lookups when
        C(service_gateway_id) is omitted.
    type: str
  vcn_id:
    description:
      - The OCID of the VCN containing the service gateway.
      - Required when creating a service gateway.
      - The module does not support moving an existing service gateway to
        another VCN.
      - Also scopes name-based service gateway lookups when
        C(service_gateway_id) is omitted.
    type: str
  service_ids:
    description:
      - The OCIDs of the OCI services the service gateway should be attached
        to.
      - When updated, this replaces the service gateway's current attached
        service set.
      - Order does not matter for drift detection.
    type: list
    elements: str
  route_table_id:
    description:
      - The OCID of the route table the service gateway should use.
    type: str
  block_traffic:
    description:
      - Whether the service gateway blocks all traffic through it.
      - This is an update-only field. It cannot be set at create time and is
        not included in the create request.
    type: bool
"""

EXAMPLES = r"""
- name: Create a service gateway
  oracle.oci.oci_service_gateway:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    name: example-service-gateway
    service_ids:
      - ocid1.service.oc1..example
    route_table_id: ocid1.routetable.oc1..example
  register: created_service_gateway

- name: Reconcile a uniquely named service gateway by name
  oracle.oci.oci_service_gateway:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    name: example-service-gateway
    service_ids:
      - ocid1.service.oc1..example
      - ocid1.service.oc1..another-example

- name: Intentionally create a second service gateway with the same display name
  oracle.oci.oci_service_gateway:
    state: present
    allow_duplicate_name: true
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    name: example-service-gateway

- name: Block traffic through the created service gateway
  oracle.oci.oci_service_gateway:
    state: present
    service_gateway_id: "{{ created_service_gateway.resource.id }}"
    block_traffic: true

- name: Delete the created service gateway
  oracle.oci.oci_service_gateway:
    state: absent
    service_gateway_id: "{{ created_service_gateway.resource.id }}"

- name: Delete a uniquely named service gateway without providing service_gateway_id
  oracle.oci.oci_service_gateway:
    state: absent
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    name: example-service-gateway
"""

RETURN = r"""
resource:
  description: The service gateway resource.
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
WAIT_FOR_SERVICE_GATEWAY_STATES = [LIFECYCLE_AVAILABLE]


def build_service_models(service_ids):
    return [
        oci.core.models.ServiceIdRequestDetails(service_id=service_id)
        for service_id in (service_ids or [])
    ]


def build_create_service_gateway_details(params):
    details = filter_none_values(
        {
            "compartment_id": params.get("compartment_id"),
            "vcn_id": params.get("vcn_id"),
            "display_name": params.get("name"),
            "route_table_id": params.get("route_table_id"),
            "services": build_service_models(params.get("service_ids")),
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
        }
    )
    return oci.core.models.CreateServiceGatewayDetails(**details)


class OciServiceGatewayModule(OciResourceBase):
    """Concrete resource adapter for OCI service gateways."""

    @property
    def client_class(self):
        return oci.core.VirtualNetworkClient

    resource_id_param = "service_gateway_id"
    list_resource_method = "list_service_gateways"
    list_filter_params = ("vcn_id",)
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "service gateway"
    update_wait_states = WAIT_FOR_SERVICE_GATEWAY_STATES
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
            "param_name": "block_traffic",
            "resource_field": "block_traffic",
            "update_field": "block_traffic",
            "is_mutable": True,
        },
        {
            "param_name": "service_ids",
            "is_mutable": True,
            "strategy": "plan_service_ids_strategy",
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
            self.client.get_service_gateway,
            service_gateway_id=resource_id,
        )

    def plan_service_ids_strategy(self, resource, resource_dict, spec, desired_value):
        current_ids = sorted(
            service.get("service_id")
            for service in (resource_dict.get("services") or [])
        )
        desired_ids = sorted(desired_value or [])
        if current_ids == desired_ids:
            return []
        return [("replace", desired_value or [])]

    def create_resource(self):
        create_service_gateway_details = build_create_service_gateway_details(
            self.module.params
        )
        response = self.call_with_retry(
            self.client.create_service_gateway,
            create_service_gateway_details=create_service_gateway_details,
        )
        return self.get_mutation_result(
            response.data,
            getattr(response.data, "id", None),
            WAIT_FOR_SERVICE_GATEWAY_STATES,
        )

    def update_resource(self, resource):
        update_plan = self.get_update_plan(resource)
        service_ids_operation = None
        for strategy_operation in update_plan["strategy_operations"]:
            if strategy_operation["param_name"] == "service_ids":
                operations = strategy_operation["operations"]
                if operations:
                    service_ids_operation = operations[0]
                break

        update_model_fields = dict(update_plan["update_model_fields"])
        if service_ids_operation is not None:
            update_model_fields["services"] = build_service_models(
                service_ids_operation[1]
            )

        if not update_model_fields:
            return resource

        update_service_gateway_details = oci.core.models.UpdateServiceGatewayDetails(
            **update_model_fields
        )
        response = self.call_with_retry(
            self.client.update_service_gateway,
            service_gateway_id=resource.id,
            update_service_gateway_details=update_service_gateway_details,
        )
        return self.get_mutation_result(
            response.data,
            resource.id,
            WAIT_FOR_SERVICE_GATEWAY_STATES,
        )

    def delete_resource(self, resource):
        return self.delete_resource_and_wait(
            resource,
            self.client.delete_service_gateway,
            service_gateway_id=resource.id,
        )


def main():
    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        service_gateway_id=dict(type="str"),
        vcn_id=dict(type="str"),
        service_ids=dict(type="list", elements="str"),
        route_table_id=dict(type="str"),
        block_traffic=dict(type="bool"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    OciServiceGatewayModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
