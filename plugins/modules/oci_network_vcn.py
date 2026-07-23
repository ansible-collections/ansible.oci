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
  - oracle.oci.oci_auth_options
  - oracle.oci.oci_wait_options
  - oracle.oci.oci_tags_options
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
      - Required for update and delete operations.
      - Must be omitted for create operations.
    type: str
  display_name:
    description:
      - Human-readable name for the VCN.
      - Required when creating a VCN.
      - Not used to identify existing VCNs for update or delete operations.
      - Re-running create without C(vcn_id) can create additional VCNs because
        OCI display names are not unique.
    type: str
  compartment_id:
    description:
      - The OCID of the compartment containing the VCN.
      - Required when creating a VCN.
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
  oracle.oci.oci_network_vcn:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    display_name: example-vcn
    cidr_blocks:
      - 10.0.0.0/16
    dns_label: examplevcn
  register: created_vcn

- name: Update the created VCN display name and tags
  oracle.oci.oci_network_vcn:
    state: present
    vcn_id: "{{ created_vcn.resource.id }}"
    display_name: example-vcn-updated
    freeform_tags:
      env: dev

- name: Add a CIDR block to the created VCN
  oracle.oci.oci_network_vcn:
    state: present
    vcn_id: "{{ created_vcn.resource.id }}"
    cidr_blocks:
      - 10.0.0.0/16
      - 10.1.0.0/16
    wait: true

- name: Delete the created VCN
  oracle.oci.oci_network_vcn:
    state: absent
    vcn_id: "{{ created_vcn.resource.id }}"
"""

RETURN = r"""
resource:
  description: The VCN resource.
  returned: when state != absent
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.oracle.oci.plugins.module_utils.oci_auth import (
    create_service_client,
)
from ansible_collections.oracle.oci.plugins.module_utils.oci_common import (
    LIFECYCLE_AVAILABLE,
    OCI_COMMON_ARGS,
    filter_none_values,
    to_dict as serialize_resource_dict,
)
from ansible_collections.oracle.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
)
from ansible_collections.oracle.oci.plugins.module_utils.oci_wait import (
    call_with_retry,
    wait_for_work_request,
)

try:
    import oci

    HAS_OCI_SDK = True
except ImportError:
    HAS_OCI_SDK = False
    oci = None

CREATE_REQUIRED_FIELDS = (
    "compartment_id",
    "cidr_blocks",
    "display_name",
)
WAIT_FOR_VCN_STATES = (LIFECYCLE_AVAILABLE,)


def build_create_vcn_details(params):
    details = filter_none_values(
        {
            "compartment_id": params.get("compartment_id"),
            "cidr_blocks": params.get("cidr_blocks"),
            "display_name": params.get("display_name"),
            "dns_label": params.get("dns_label"),
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
        }
    )
    return oci.core.models.CreateVcnDetails(**details)


def build_update_vcn_details(params):
    details = filter_none_values(
        {
            "display_name": params.get("display_name"),
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
        }
    )
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
            return [("modify", removals[0], additions[0])]
        raise ValueError(
            "Complex cidr_blocks changes are not supported by "
            "oci_network_vcn. Apply the CIDR updates in smaller steps."
        )
    if additions:
        return [("add", cidr_block) for cidr_block in additions]
    return [("remove", cidr_block) for cidr_block in removals]


class OciNetworkVcnModule(OciResourceBase):
    """Concrete resource adapter for OCI VCNs."""

    client_class = oci.core.VirtualNetworkClient if HAS_OCI_SDK else object()
    resource_id_param = "vcn_id"
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "VCN"
    known_field_names = ("display_name",)

    def __init__(self, module):
        super().__init__(module)
        self.work_request_client = None
        if HAS_OCI_SDK:
            self.work_request_client = create_service_client(
                module, oci.work_requests.WorkRequestClient
            )

    def get_resource_response(self, resource_id):
        return call_with_retry(
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

    def _metadata_update_needed(self, resource_dict):
        desired_display_name = self.module.params.get("display_name")
        if desired_display_name is not None and resource_dict.get("display_name") != desired_display_name:
            return True

        desired_freeform_tags = self.module.params.get("freeform_tags")
        if desired_freeform_tags is not None and resource_dict.get("freeform_tags") != desired_freeform_tags:
            return True

        desired_defined_tags = self.module.params.get("defined_tags")
        if desired_defined_tags is not None and resource_dict.get("defined_tags") != desired_defined_tags:
            return True

        return False

    def _wait_for_vcn_work_request(self, response):
        if not self.module.params.get("wait", True):
            return None

        work_request_id = getattr(response, "headers", {}).get("opc-work-request-id")
        if not work_request_id or self.work_request_client is None:
            return None

        return wait_for_work_request(
            self.module,
            self.work_request_client,
            work_request_id,
        )

    def _apply_cidr_operation(self, vcn_id, cidr_operation):
        operation_name = cidr_operation[0]

        if operation_name == "add":
            response = call_with_retry(
                self.client.add_vcn_cidr,
                vcn_id=vcn_id,
                add_vcn_cidr_details=build_add_vcn_cidr_details(cidr_operation[1]),
            )
        elif operation_name == "modify":
            response = call_with_retry(
                self.client.modify_vcn_cidr,
                vcn_id=vcn_id,
                modify_vcn_cidr_details=build_modify_vcn_cidr_details(
                    cidr_operation[1],
                    cidr_operation[2],
                ),
            )
        elif operation_name == "remove":
            response = call_with_retry(
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
        response = call_with_retry(
            self.client.create_vcn,
            create_vcn_details=create_vcn_details,
        )
        return self.get_mutation_result(
            response.data,
            getattr(response.data, "id", None),
            WAIT_FOR_VCN_STATES,
        )

    def update_resource(self, resource):
        resource_dict = serialize_resource_dict(resource)
        cidr_operations = self._planned_cidr_operations(resource_dict)
        current_resource = resource

        if cidr_operations:
            for cidr_operation in cidr_operations:
                current_resource = self._apply_cidr_operation(resource.id, cidr_operation)
            resource_dict = serialize_resource_dict(current_resource)

        if not self._metadata_update_needed(resource_dict):
            return current_resource if cidr_operations else resource

        update_vcn_details = build_update_vcn_details(self.module.params)
        response = call_with_retry(
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

    def needs_update(self, resource) -> bool:
        resource_dict = serialize_resource_dict(resource)

        desired_dns_label = self.module.params.get("dns_label")
        if desired_dns_label is not None and resource_dict.get("dns_label") != desired_dns_label:
            self.module.fail_json(
                msg=(
                    "Updating dns_label for an existing VCN is not supported "
                    "because OCI treats dns_label as immutable after create."
                )
            )

        cidr_operations = self._planned_cidr_operations(resource_dict)
        if cidr_operations:
            return True

        desired_display_name = self.module.params.get("display_name")
        if desired_display_name is not None and resource_dict.get("display_name") != desired_display_name:
            return True

        return False


def main():
    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        vcn_id=dict(type="str"),
        display_name=dict(type="str"),
        compartment_id=dict(type="str"),
        cidr_blocks=dict(type="list", elements="str"),
        dns_label=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    OciNetworkVcnModule(module).run()


if __name__ == "__main__":
    main()
