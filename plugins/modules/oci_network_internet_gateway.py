# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_network_internet_gateway
short_description: Manage an Internet Gateway resource in Oracle Cloud Infrastructure
description:
  - Create, update, and delete OCI internet gateways.
  - Uses the shared OCI helper layer for authentication, waiting, retry
    behavior, and result shaping.
  - Create requests must omit C(internet_gateway_id). After create, capture the
    returned internet gateway ID and use it for later C(state=present) and
    C(state=absent) tasks.
version_added: "1.0.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_name_lookup_options
  - ansible.oci.oci_wait_options
  - ansible.oci.oci_tags_options
options:
  state:
    description:
      - The desired lifecycle state of the internet gateway.
    type: str
    choices: [present, absent]
    default: present
  internet_gateway_id:
    description:
      - The OCID of the internet gateway.
      - When provided, the module manages this exact internet gateway.
      - Required to distinguish between multiple internet gateways that share
        the same scoped C(name).
    type: str
  name:
    description:
      - Human-readable name for the internet gateway.
      - Required when creating an internet gateway.
      - When C(internet_gateway_id) is omitted, the module uses
        C(compartment_id + vcn_id + name) to find an existing internet
        gateway.
      - If exactly one internet gateway matches, C(state=present) manages it
        as the update target and C(state=absent) deletes it.
      - If more than one internet gateway matches, the task fails and the
        caller must supply C(internet_gateway_id).
    type: str
  compartment_id:
    description:
      - The OCID of the compartment containing the internet gateway.
      - Required when creating an internet gateway.
      - The module does not move an existing internet gateway to another
        compartment.
      - Also scopes name-based internet gateway lookups when
        C(internet_gateway_id) is omitted.
    type: str
  vcn_id:
    description:
      - The OCID of the VCN containing the internet gateway.
      - Required when creating an internet gateway.
      - The module does not support moving an existing internet gateway to
        another VCN.
      - Also scopes name-based internet gateway lookups when
        C(internet_gateway_id) is omitted.
    type: str
  is_enabled:
    description:
      - Whether the internet gateway is enabled.
      - Defaults to C(true) when creating a new internet gateway.
      - When omitted while updating an existing internet gateway, the
        current enabled/disabled state is left unchanged rather than being
        reset to C(true).
    type: bool
  route_table_id:
    description:
      - The OCID of a route table to associate directly with the internet
        gateway, for OCI's transit routing feature. This controls how
        traffic arriving through this gateway is routed once it enters the
        VCN, separately from the route table assigned to any subnet.
      - This is an optional, advanced setting. Most deployments do not need
        it and can omit it; only set it if you are implementing transit
        routing. Omitting it leaves traffic subject to each subnet's own
        route table as usual.
      - Because a route table's own rules may need to reference this
        gateway's OCID (see C(network_entity_id) on
        C(ansible.oci.oci_network_route_table)), create the gateway first without
        C(route_table_id), create the route table referencing the gateway,
        then update the gateway with C(route_table_id) if transit routing is
        required. See the examples below.
    type: str
"""

EXAMPLES = r"""
- name: Create an internet gateway with only the required parameters
  ansible.oci.oci_network_internet_gateway:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    name: example-internet-gateway
  register: created_internet_gateway

- name: Create a route table with a rule pointing at that internet gateway
  ansible.oci.oci_network_route_table:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    name: example-route-table
    route_rules:
      - destination: 0.0.0.0/0
        network_entity_id: "{{ created_internet_gateway.resource.id }}"
  register: created_route_table

- name: (Optional) enable transit routing by pointing the gateway back at that route table
  ansible.oci.oci_network_internet_gateway:
    state: present
    internet_gateway_id: "{{ created_internet_gateway.resource.id }}"
    route_table_id: "{{ created_route_table.resource.id }}"

- name: Reconcile a uniquely named internet gateway by name
  ansible.oci.oci_network_internet_gateway:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    name: example-internet-gateway
    is_enabled: false

- name: Delete the created internet gateway
  ansible.oci.oci_network_internet_gateway:
    state: absent
    internet_gateway_id: "{{ created_internet_gateway.resource.id }}"

- name: Delete a uniquely named internet gateway without providing internet_gateway_id
  ansible.oci.oci_network_internet_gateway:
    state: absent
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    name: example-internet-gateway
"""

RETURN = r"""
resource:
  description: The internet gateway resource.
  returned: when state != absent
  type: dict
  contains:
    id:
      description: The OCID of the internet gateway.
      type: str
      returned: always
      sample: ocid1.internetgateway.oc1..example
    name:
      description: The display name of the internet gateway.
      type: str
      returned: always
      sample: example-internet-gateway
    compartment_id:
      description: The OCID of the compartment containing the internet gateway.
      type: str
      returned: always
      sample: ocid1.compartment.oc1..example
    vcn_id:
      description: The OCID of the VCN containing the internet gateway.
      type: str
      returned: always
      sample: ocid1.vcn.oc1..example
    lifecycle_state:
      description: The current lifecycle state of the internet gateway.
      type: str
      returned: always
      sample: AVAILABLE
    is_enabled:
      description: Whether the internet gateway is enabled.
      type: bool
      returned: always
      sample: true
    route_table_id:
      description: The OCID of the route table directly associated with the internet gateway, if any.
      type: str
      returned: always
      sample: null
    freeform_tags:
      description: Free-form tags applied to the internet gateway.
      type: dict
      returned: always
      sample: {"environment": "production"}
    defined_tags:
      description: Defined tags applied to the internet gateway.
      type: dict
      returned: always
      sample: {"Operations": {"CostCenter": "42"}}
    time_created:
      description: The date and time the internet gateway was created, in RFC3339 format.
      type: str
      returned: always
      sample: "2026-01-01T00:00:00.000Z"
  sample:
    id: ocid1.internetgateway.oc1..example
    name: example-internet-gateway
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    lifecycle_state: AVAILABLE
    is_enabled: true
    route_table_id: null
    freeform_tags: {"environment": "production"}
    defined_tags: {"Operations": {"CostCenter": "42"}}
    time_created: "2026-01-01T00:00:00.000Z"
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    LIFECYCLE_AVAILABLE,
    OCI_COMMON_ARGS,
    filter_none_values,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
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
WAIT_FOR_IG_STATES = [LIFECYCLE_AVAILABLE]


def build_create_internet_gateway_details(params):
    is_enabled = params.get("is_enabled")
    details = filter_none_values(
        {
            "compartment_id": params.get("compartment_id"),
            "vcn_id": params.get("vcn_id"),
            "display_name": params.get("name"),
            "is_enabled": True if is_enabled is None else is_enabled,
            "route_table_id": params.get("route_table_id"),
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
        }
    )
    return oci.core.models.CreateInternetGatewayDetails(**details)


class OciNetworkInternetGatewayModule(OciResourceBase):
    """Concrete resource adapter for OCI internet gateways.

    The OCI SDK uses the ``ig_id`` keyword argument for
    ``get_internet_gateway``, ``update_internet_gateway``, and
    ``delete_internet_gateway``, while this collection's ansible-facing
    parameter is named ``internet_gateway_id`` (matching the ``subnet_id`` /
    ``vcn_id`` / ``route_table_id`` naming style used elsewhere). Because
    ``resource_id_param`` (used for module.params lookups and error messages)
    does not match the literal SDK kwarg name, every SDK call below maps the
    resource id to ``ig_id`` explicitly instead of relying on the default
    metadata-driven update flow.
    """

    @property
    def client_class(self):
        return oci.core.VirtualNetworkClient

    resource_id_param = "internet_gateway_id"
    list_resource_method = "list_internet_gateways"
    list_filter_params = ("vcn_id",)
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "internet gateway"
    update_wait_states = WAIT_FOR_IG_STATES
    update_field_specs = [
        {
            "param_name": "name",
            "resource_field": "display_name",
            "update_field": "display_name",
            "is_mutable": True,
        },
        {
            "param_name": "is_enabled",
            "resource_field": "is_enabled",
            "update_field": "is_enabled",
            "is_mutable": True,
        },
        {
            "param_name": "route_table_id",
            "resource_field": "route_table_id",
            "update_field": "route_table_id",
            "is_mutable": True,
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
            self.client.get_internet_gateway,
            ig_id=resource_id,
        )

    def create_resource(self):
        create_internet_gateway_details = build_create_internet_gateway_details(
            self.module.params
        )
        response = self.call_with_retry(
            self.client.create_internet_gateway,
            create_internet_gateway_details=create_internet_gateway_details,
        )
        return self.get_mutation_result(
            response.data,
            getattr(response.data, "id", None),
            WAIT_FOR_IG_STATES,
        )

    def build_update_details(self, update_model_fields):
        return oci.core.models.UpdateInternetGatewayDetails(**update_model_fields)

    def update_resource(self, resource):
        # The base OciResourceBase.update_resource() builds SDK kwargs from
        # resource_id_param directly, which would incorrectly call
        # update_internet_gateway(internet_gateway_id=...). The real SDK
        # kwarg is "ig_id", so this override reuses the shared update plan
        # but issues the SDK call with the correct kwarg name.
        update_plan = self.get_update_plan(resource)
        if not update_plan["update_model_fields"]:
            return resource

        update_details = self.build_update_details(update_plan["update_model_fields"])
        response = self.call_with_retry(
            self.client.update_internet_gateway,
            ig_id=resource.id,
            update_internet_gateway_details=update_details,
        )
        return self.get_mutation_result(
            response.data,
            resource.id,
            WAIT_FOR_IG_STATES,
        )

    def delete_resource(self, resource):
        return self.delete_resource_and_wait(
            resource,
            self.client.delete_internet_gateway,
            ig_id=resource.id,
        )


def main():
    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        internet_gateway_id=dict(type="str"),
        vcn_id=dict(type="str"),
        is_enabled=dict(type="bool"),
        route_table_id=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    OciNetworkInternetGatewayModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
