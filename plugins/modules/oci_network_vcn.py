# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_network_vcn
short_description: Manage a Virtual Cloud Network resource in Oracle Cloud Infrastructure
description:
  - Create, update, and delete OCI Virtual Cloud Networks (VCNs).
  - Uses the shared OCI helper layer for authentication, waiting, retry
    behavior, and result shaping.
  - Create requests must omit C(vcn_id). After create, capture the returned
    VCN ID and use it for later C(state=present) and C(state=absent) tasks.
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
      - The desired lifecycle state of the VCN.
    type: str
    choices: [present, absent]
    default: present
  vcn_id:
    description:
      - The OCID of the VCN.
      - When provided, the module manages this exact VCN.
      - Required to distinguish between multiple VCNs that share the same
        C(name).
    type: str
  name:
    description:
      - Human-readable name for the VCN.
      - Required when creating a VCN.
      - When C(vcn_id) is omitted, the module uses
        C(compartment_id + name) to find an existing VCN.
      - If exactly one VCN matches, C(state=present) manages it as the update
        target and C(state=absent) deletes it.
      - If more than one VCN matches, the task fails and the caller must supply
        C(vcn_id).
    type: str
  compartment_id:
    description:
      - The OCID of the compartment containing the VCN.
      - Required when creating a VCN.
      - Also scopes name-based VCN lookups when C(vcn_id) is omitted.
    type: str
  cidr_blocks:
    description:
      - The IPv4 CIDR blocks for the VCN.
      - Required when creating a VCN.
      - Supports safe common-case CIDR updates for existing VCNs.
      - The module can add CIDR blocks, remove CIDR blocks, or modify a single
        unambiguous CIDR block replacement.
      - More complex multi-block reshuffles are rejected and should be applied
        incrementally.
      - CIDR block updates require C(wait=true) because OCI processes them as
        asynchronous work requests.
    type: list
    elements: str
  dns_label:
    description:
      - The DNS label for the VCN.
      - The OCI API treats this as create-time only.
    type: str
"""

EXAMPLES = r"""
- name: Create a VCN
  ansible.oci.oci_network_vcn:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    name: example-vcn
    cidr_blocks:
      - 10.0.0.0/16
    dns_label: examplevcn
  register: created_vcn

- name: Reconcile a uniquely named VCN by name
  ansible.oci.oci_network_vcn:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    name: example-vcn
    cidr_blocks:
      - 10.0.0.0/16
    freeform_tags:
      env: dev

- name: Intentionally create a second VCN with the same display name
  ansible.oci.oci_network_vcn:
    state: present
    allow_duplicate_name: true
    compartment_id: ocid1.compartment.oc1..example
    name: example-vcn
    cidr_blocks:
      - 10.1.0.0/16
    dns_label: examplevcncopy

- name: Add a CIDR block to the created VCN
  ansible.oci.oci_network_vcn:
    state: present
    vcn_id: "{{ created_vcn.resource.id }}"
    cidr_blocks:
      - 10.0.0.0/16
      - 10.1.0.0/16
    wait: true

- name: Delete the created VCN
  ansible.oci.oci_network_vcn:
    state: absent
    vcn_id: "{{ created_vcn.resource.id }}"

- name: Delete a uniquely named VCN without providing vcn_id
  ansible.oci.oci_network_vcn:
    state: absent
    compartment_id: ocid1.compartment.oc1..example
    name: example-vcn
"""

RETURN = r"""
resource:
  description: The VCN resource.
  returned: when state != absent
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_auth import (
    create_service_client,
)
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
    "cidr_blocks",
    "name",
]
WAIT_FOR_VCN_STATES = [LIFECYCLE_AVAILABLE]


def build_create_vcn_details(params):
    details = filter_none_values(
        {
            "compartment_id": params.get("compartment_id"),
            "cidr_blocks": params.get("cidr_blocks"),
            "display_name": params.get("name"),
            "dns_label": params.get("dns_label"),
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
        }
    )
    return oci.core.models.CreateVcnDetails(**details)


def build_update_vcn_details(params):
    details = filter_none_values(dict(params))
    return oci.core.models.UpdateVcnDetails(**details)


def build_add_vcn_cidr_details(cidr_block):
    return oci.core.models.AddVcnCidrDetails(cidr_block=cidr_block)


def build_modify_vcn_cidr_details(original_cidr_block, new_cidr_block):
    return oci.core.models.ModifyVcnCidrDetails(
        original_cidr_block=original_cidr_block,
        new_cidr_block=new_cidr_block,
    )


def build_remove_vcn_cidr_details(cidr_block):
    return oci.core.models.RemoveVcnCidrDetails(cidr_block=cidr_block)


def _ordered_difference(source_values, excluded_values):
    excluded_set = set(excluded_values)
    return [value for value in source_values if value not in excluded_set]


def plan_vcn_cidr_operations(current_cidr_blocks, desired_cidr_blocks):
    additions = _ordered_difference(desired_cidr_blocks, current_cidr_blocks)
    removals = _ordered_difference(current_cidr_blocks, desired_cidr_blocks)

    if not additions and not removals:
        return []
    if additions and removals:
        if len(additions) == 1 and len(removals) == 1:
            return [tuple(["modify", removals[0], additions[0]])]
        raise ValueError(
            "Complex cidr_blocks changes are not supported by "
            "oci_network_vcn. Apply the CIDR updates in smaller steps."
        )
    if additions:
        return [tuple(["add", cidr_block]) for cidr_block in additions]
    return [tuple(["remove", cidr_block]) for cidr_block in removals]


class OciNetworkVcnModule(OciResourceBase):
    """Concrete resource adapter for OCI VCNs."""

    @property
    def client_class(self):
        return oci.core.VirtualNetworkClient

    resource_id_param = "vcn_id"
    list_resource_method = "list_vcns"
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "VCN"
    update_field_specs = [
        {
            "param_name": "cidr_blocks",
            "resource_field": "cidr_blocks",
            "is_mutable": True,
            "strategy": "plan_cidr_blocks_strategy",
        },
        {
            "param_name": "name",
            "resource_field": "display_name",
            "update_field": "display_name",
            "is_mutable": True,
        },
        {
            "param_name": "dns_label",
            "resource_field": "dns_label",
            "is_mutable": False,
            "immutable_reason": "OCI treats dns_label as immutable after create",
        },
    ]

    def __init__(self, module):
        super().__init__(module)
        self.work_request_client = None
        if HAS_OCI_SDK:
            self.work_request_client = create_service_client(
                module, oci.work_requests.WorkRequestClient
            )

    def get_resource_response(self, resource_id):
        return self.call_with_retry(
            self.client.get_vcn,
            vcn_id=resource_id,
        )

    def _current_cidr_blocks(self, resource_dict):
        current_cidr_blocks = resource_dict.get("cidr_blocks")
        if current_cidr_blocks is None and resource_dict.get("cidr_block") is not None:
            current_cidr_blocks = [resource_dict.get("cidr_block")]
        return list(current_cidr_blocks or [])

    def _planned_cidr_operations(self, resource_dict):
        desired_cidr_blocks = self._desired_cidr_blocks()
        if desired_cidr_blocks is None:
            return []

        current_cidr_blocks = self._current_cidr_blocks(resource_dict)
        if sorted(current_cidr_blocks) == sorted(desired_cidr_blocks):
            return []

        if not self.module.params.get("wait", True):
            self.module.fail_json(
                msg=(
                    "Updating cidr_blocks for an existing VCN requires "
                    "wait=true in oci_network_vcn."
                )
            )

        try:
            return plan_vcn_cidr_operations(current_cidr_blocks, desired_cidr_blocks)
        except ValueError as exc:
            self.module.fail_json(msg=str(exc))
        return []

    def plan_cidr_blocks_strategy(self, resource, resource_dict, spec, desired_value):
        return self._planned_cidr_operations(resource_dict)

    def _wait_for_vcn_work_request(self, response):
        if not self.module.params.get("wait", True):
            return None

        work_request_id = getattr(response, "headers", {}).get("opc-work-request-id")
        if not work_request_id or self.work_request_client is None:
            return None

        return self.wait_for_work_request(
            self.work_request_client,
            work_request_id,
        )

    def _apply_cidr_operation(self, vcn_id, cidr_operation):
        operation_name = cidr_operation[0]

        if operation_name == "add":
            response = self.call_with_retry(
                self.client.add_vcn_cidr,
                vcn_id=vcn_id,
                add_vcn_cidr_details=build_add_vcn_cidr_details(cidr_operation[1]),
            )
        elif operation_name == "modify":
            response = self.call_with_retry(
                self.client.modify_vcn_cidr,
                vcn_id=vcn_id,
                modify_vcn_cidr_details=build_modify_vcn_cidr_details(
                    cidr_operation[1],
                    cidr_operation[2],
                ),
            )
        elif operation_name == "remove":
            response = self.call_with_retry(
                self.client.remove_vcn_cidr,
                vcn_id=vcn_id,
                remove_vcn_cidr_details=build_remove_vcn_cidr_details(cidr_operation[1]),
            )
        else:
            raise ValueError(f"Unsupported VCN CIDR operation: {operation_name}")

        self._wait_for_vcn_work_request(response)
        return self.wait_for_resource_id(vcn_id, WAIT_FOR_VCN_STATES)

    def create_resource(self):
        create_vcn_details = build_create_vcn_details(self.module.params)
        response = self.call_with_retry(
            self.client.create_vcn,
            create_vcn_details=create_vcn_details,
        )
        return self.get_mutation_result(
            response.data,
            getattr(response.data, "id", None),
            WAIT_FOR_VCN_STATES,
        )

    def update_resource(self, resource):
        update_plan = self.get_update_plan(resource)
        cidr_operations = []
        for strategy_operation in update_plan["strategy_operations"]:
            if strategy_operation["param_name"] == "cidr_blocks":
                cidr_operations = strategy_operation["operations"]
                break
        current_resource = resource

        if cidr_operations:
            for cidr_operation in cidr_operations:
                current_resource = self._apply_cidr_operation(resource.id, cidr_operation)
            update_plan = self.get_update_plan(current_resource)

        if not update_plan["update_model_fields"]:
            return current_resource if cidr_operations else resource

        update_vcn_details = build_update_vcn_details(update_plan["update_model_fields"])
        response = self.call_with_retry(
            self.client.update_vcn,
            vcn_id=resource.id,
            update_vcn_details=update_vcn_details,
        )
        return self.get_mutation_result(
            response.data,
            resource.id,
            WAIT_FOR_VCN_STATES,
        )

    def delete_resource(self, resource):
        return self.delete_resource_and_wait(
            resource,
            self.client.delete_vcn,
            vcn_id=resource.id,
        )

    def _desired_cidr_blocks(self):
        desired_cidr_blocks = self.module.params.get("cidr_blocks")
        if desired_cidr_blocks is None:
            return None
        return list(desired_cidr_blocks)


def main():
    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        vcn_id=dict(type="str"),
        cidr_blocks=dict(type="list", elements="str"),
        dns_label=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    OciNetworkVcnModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
