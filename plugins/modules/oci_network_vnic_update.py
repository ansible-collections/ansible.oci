# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_network_vnic_update
short_description: Update a VNIC in Oracle Cloud Infrastructure
description:
  - Update an existing VNIC after instance creation.
version_added: "1.2.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_wait_options
  - ansible.oci.oci_tags_options
options:
  vnic_id:
    description:
      - The OCID of the existing VNIC to update.
      - Use M(ansible.oci.oci_vnic_attachment_info) to find the VNIC OCID.
    type: str
    required: true
  name:
    description:
      - A user-friendly VNIC name.
      - This value can be updated.
    type: str
  hostname_label:
    description:
      - The hostname label for the VNIC primary private IP.
      - The label must be unique in the subnet and meet RFC 952 and RFC 1123 requirements.
    type: str
  nsg_ids:
    description:
      - The OCIDs of the network security groups for the VNIC.
      - Set an empty list to remove the VNIC from all network security groups.
      - A change to the list order does not cause an update.
      - OCI ignores this option for VNICs in a VLAN.
    type: list
    elements: str
  skip_source_dest_check:
    description:
      - Whether to disable source and destination checks on the VNIC.
      - Omit this option to preserve the current value.
      - OCI ignores this option for VNICs in a VLAN.
    type: bool
  route_table_id:
    description:
      - The OCID of the route table for the VNIC.
    type: str
  security_attributes:
    description:
      - Security attributes for Zero Trust Packet Routing policies.
      - Keys identify security namespaces and attributes. Values retain their supplied types.
    type: dict
notes:
  - Omitted update options leave the corresponding VNIC fields unchanged.
"""

EXAMPLES = r"""
- name: Update a VNIC
  ansible.oci.oci_network_vnic_update:
    vnic_id: ocid1.vnic.oc1..example
    name: application-vnic
    hostname_label: application
    nsg_ids:
      - ocid1.networksecuritygroup.oc1..example
    skip_source_dest_check: true

- name: Remove NSG membership and enable source and destination checks
  ansible.oci.oci_network_vnic_update:
    vnic_id: ocid1.vnic.oc1..example
    name: application-vnic
    nsg_ids: []
    skip_source_dest_check: false
"""

RETURN = r"""
resource:
  description: The current VNIC after the requested update.
  returned: In normal mode, or when check mode predicts no change.
  type: dict
  contains:
    id:
      description: The OCID of the VNIC.
      type: str
    name:
      description: The VNIC display name.
      type: str
    lifecycle_state:
      description: The VNIC lifecycle state.
      type: str
    nsg_ids:
      description: The VNIC network security groups.
      type: list
      elements: str
    hostname_label:
      description: The hostname label for the primary private IP.
      type: str
    skip_source_dest_check:
      description: Whether source and destination checks are disabled.
      type: bool
    route_table_id:
      description: The OCID of the VNIC route table.
      type: str
    security_attributes:
      description: Security attributes assigned to the VNIC.
      type: dict
    freeform_tags:
      description: Free-form tags assigned to the VNIC.
      type: dict
    defined_tags:
      description: Defined tags assigned to the VNIC.
      type: dict
    is_primary:
      description: Whether this VNIC is the primary VNIC of the instance.
      type: bool
    subnet_id:
      description: The subnet OCID for a VNIC in a subnet.
      type: str
    vlan_id:
      description: The VLAN OCID for a VNIC in a VLAN.
      type: str
    private_ip:
      description: The primary private IP address.
      type: str
    public_ip:
      description: The public IP address, when assigned.
      type: str
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    LIFECYCLE_AVAILABLE,
    OCI_AUTH_ARGS,
    OCI_TAG_ARGS,
    OCI_WAIT_ARGS,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
    UpdateFieldSpec,
)

oci = import_oci_sdk()[0]


class OciNetworkVnicUpdateModule(OciResourceBase):
    """Manage updates for an existing OCI VNIC."""

    @property
    def client_class(self):
        """Return the OCI virtual network client class.

        Returns:
            The SDK client class.
        """
        return oci.core.VirtualNetworkClient

    resource_id_param = "vnic_id"
    name_lookup_param = None
    create_resource_name = "VNIC"
    update_method_name = "update_vnic"
    update_details_name = "update_vnic_details"
    update_wait_states = (LIFECYCLE_AVAILABLE,)
    update_field_specs = (
        UpdateFieldSpec(
            param_name="name",
            resource_field="display_name",
            is_mutable=True,
        ),
        UpdateFieldSpec(param_name="hostname_label", is_mutable=True),
        UpdateFieldSpec(
            param_name="nsg_ids", is_mutable=True, compare="sorted_list"
        ),
        UpdateFieldSpec(param_name="skip_source_dest_check", is_mutable=True),
        UpdateFieldSpec(param_name="route_table_id", is_mutable=True),
        UpdateFieldSpec(param_name="security_attributes", is_mutable=True),
    )

    def get_resource_response(self, resource_id):
        """Return the OCI response for one VNIC.

        Args:
            resource_id: VNIC OCID.

        Returns:
            OCI response containing the VNIC.
        """
        return self.call_with_retry(self.client.get_vnic, vnic_id=resource_id)

    def fail_missing_update_target(self):
        """Fail when the required VNIC OCID does not identify a resource.

        The inherited message offers resource creation, but this module only
        updates existing VNICs.
        """
        self.module.fail_json(
            msg=(
                "No VNIC was found for vnic_id="
                f"{self.resource_id}. The VNIC must already exist."
            )
        )

    def create_resource(self):
        """Reject creation because OCI VNIC creation uses another workflow."""
        self.module.fail_json(msg="Creating a VNIC is not supported")

    def delete_resource(self, resource):
        """Reject deletion because this module only updates VNICs.

        Args:
            resource: Existing VNIC selected by the module.
        """
        self.module.fail_json(msg="Deleting a VNIC is not supported")

    def build_update_details(self, update_model_fields):
        """Build OCI update details from the planned field changes.

        Args:
            update_model_fields: Fields selected by the shared update planner.

        Returns:
            An OCI ``UpdateVnicDetails`` model.
        """
        return oci.core.models.UpdateVnicDetails(**update_model_fields)

    def build_update_plan(self, resource):
        """Exclude VLAN fields because the inherited planner compares them.

        Args:
            resource: Current OCI VNIC model.

        Returns:
            The shared update plan, adjusted for VLAN VNIC behavior.
        """
        plan = super().build_update_plan(resource)
        if getattr(resource, "vlan_id", None):
            plan["update_model_fields"].pop("nsg_ids", None)
            plan["update_model_fields"].pop("skip_source_dest_check", None)
            plan["update_needed"] = bool(
                plan["update_model_fields"] or plan["strategy_operations"]
            )
        return plan


def main():
    """Run the VNIC update module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        **OCI_WAIT_ARGS,
        **OCI_TAG_ARGS,
        vnic_id=dict(type="str", required=True),
        name=dict(type="str"),
        hostname_label=dict(type="str"),
        nsg_ids=dict(type="list", elements="str"),
        skip_source_dest_check=dict(type="bool"),
        route_table_id=dict(type="str"),
        security_attributes=dict(type="dict"),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    if not module.params.get("vnic_id"):
        module.fail_json(msg="vnic_id is required and cannot be empty")
    OciNetworkVnicUpdateModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
