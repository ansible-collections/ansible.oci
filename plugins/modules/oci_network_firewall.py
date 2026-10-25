# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = r"""
---
module: oci_network_firewall
short_description: Manage an OCI Network Firewall
description:
  - Create, update, and delete OCI Network Firewall resources.
version_added: 1.2.0
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_name_lookup_options
  - ansible.oci.oci_wait_options
  - ansible.oci.oci_tags_options
options:
  state:
    description: The desired lifecycle state.
    type: str
    choices:
      - present
      - absent
    default: present
  network_firewall_id:
    description: The OCID of the Network Firewall. Use this value for updates and deletion.
    type: str
  name:
    description:
      - The resource display name.
      - Required for creation. Without a resource ID, name lookup uses the supplied compartment.
    type: str
  compartment_id:
    description:
      - The OCID of the compartment that contains the resource.
      - Required for creation and name lookup. This module cannot change the compartment.
    type: str
  network_firewall_policy_id:
    description:
      - The OCID of the associated Network Firewall policy.
      - Required for creation. This value can change after creation.
    type: str
  subnet_id:
    description:
      - The OCID of the subnet.
      - This value cannot change after creation.
      - Required for creation.
    type: str
  availability_domain:
    description:
      - The availability domain for the firewall.
      - This value cannot change after creation.
    type: str
  ipv4_address:
    description:
      - The IPv4 address assigned to the firewall.
      - This value cannot change after creation.
    type: str
  ipv6_address:
    description:
      - The IPv6 address assigned to the firewall.
      - This value cannot change after creation.
    type: str
  network_security_group_ids:
    description: Network Security Group OCIDs associated with the firewall.
    type: list
    elements: str
notes:
  - When C(wait=false), the module returns the immediate response or the resource ID without polling.
"""

EXAMPLES = r"""
- name: Create a Network Firewall
  ansible.oci.oci_network_firewall:
    compartment_id: ocid1.compartment.oc1..example
    subnet_id: ocid1.subnet.oc1..example
    network_firewall_policy_id: ocid1.networkfirewallpolicy.oc1..example
    name: example-firewall
    wait_timeout: 3600

- name: Update a Network Firewall
  ansible.oci.oci_network_firewall:
    network_firewall_id: ocid1.networkfirewall.oc1..example
    name: updated-firewall

- name: Delete a Network Firewall
  ansible.oci.oci_network_firewall:
    state: absent
    network_firewall_id: ocid1.networkfirewall.oc1..example
"""

RETURN = r"""
resource:
  description: The Network Firewall resource. The name field maps to the OCI display name.
  returned: when state is present, except when check mode predicts a change
  type: dict
  contains:
    id:
      description: The firewall OCID.
      type: str
    compartment_id:
      description: The compartment OCID.
      type: str
    name:
      description: The firewall display name.
      type: str
    subnet_id:
      description: The subnet OCID.
      type: str
    ipv4_address:
      description: The assigned IPv4 address.
      type: str
    ipv6_address:
      description: The assigned IPv6 address.
      type: str
    network_firewall_policy_id:
      description: The associated policy OCID.
      type: str
    availability_domain:
      description: The availability domain.
      type: str
    nat_configuration:
      description: NAT configuration for the firewall.
      type: dict
      contains:
        must_enable_private_nat:
          description: Whether private NAT must be enabled.
          type: bool
        nat_ip_address_list:
          description: NAT IP addresses.
          type: list
          elements: str
    shape:
      description: The firewall shape.
      type: str
    network_security_group_ids:
      description: Network Security Group OCIDs associated with the firewall.
      type: list
      elements: str
    time_created:
      description: The creation time in UTC.
      type: str
    time_updated:
      description: The last update time in UTC.
      type: str
    lifecycle_state:
      description: The lifecycle state. OCI returns uppercase values.
      type: str
    lifecycle_details:
      description: Details about the lifecycle state.
      type: str
    freeform_tags:
      description: Free-form tags for the resource.
      type: dict
    defined_tags:
      description: Defined tags for the resource.
      type: dict
    system_tags:
      description: System tags for the resource.
      type: dict
    security_attributes:
      description: Security attributes for the resource.
      type: dict
  sample:
    id: ocid1.networkfirewall.oc1..example
    compartment_id: ocid1.compartment.oc1..example
    name: example-firewall
    subnet_id: ocid1.subnet.oc1..example
    ipv4_address: 10.0.0.10
    ipv6_address: null
    network_firewall_policy_id: ocid1.networkfirewallpolicy.oc1..example
    availability_domain: Uocm:PHX-AD-1
    nat_configuration:
      must_enable_private_nat: false
      nat_ip_address_list: []
    shape: null
    network_security_group_ids: []
    time_created: '2026-01-01T00:00:00+00:00'
    time_updated: '2026-01-01T00:00:00+00:00'
    lifecycle_state: ACTIVE
    lifecycle_details: null
    freeform_tags: {}
    defined_tags: {}
    system_tags: {}
    security_attributes: {}
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    LIFECYCLE_ACTIVE,
    OCI_COMMON_ARGS,
    filter_none_values,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
    UpdateFieldSpec,
)

imported_oci_sdk = import_oci_sdk()
oci = imported_oci_sdk[0]
CREATE_REQUIRED_FIELDS = [
    "compartment_id",
    "subnet_id",
    "network_firewall_policy_id",
    "name",
]
WAIT_FOR_NETWORK_FIREWALL_STATES = [LIFECYCLE_ACTIVE]


def build_create_network_firewall_details(params):
    """Build the OCI create model from module parameters.

    Args:
        params: The validated module parameters.

    Returns:
        The OCI create details model.
    """
    details = filter_none_values(
        {
            "compartment_id": params.get("compartment_id"),
            "subnet_id": params.get("subnet_id"),
            "network_firewall_policy_id": params.get("network_firewall_policy_id"),
            "display_name": params.get("name"),
            "availability_domain": params.get("availability_domain"),
            "ipv4_address": params.get("ipv4_address"),
            "ipv6_address": params.get("ipv6_address"),
            "network_security_group_ids": params.get("network_security_group_ids"),
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
        }
    )
    return oci.network_firewall.models.CreateNetworkFirewallDetails(**details)


class OciNetworkFirewallModule(OciResourceBase):
    """Manage OCI Network Firewalls."""

    @property
    def client_class(self):
        """Return the OCI service client class.

        Returns:
            The OCI service client class.
        """
        return oci.network_firewall.NetworkFirewallClient

    resource_id_param = "network_firewall_id"
    list_resource_method = "list_network_firewalls"
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "Network Firewall"
    update_method_name = "update_network_firewall"
    update_details_name = "update_network_firewall_details"
    update_wait_states = WAIT_FOR_NETWORK_FIREWALL_STATES
    update_field_specs = (
        UpdateFieldSpec(
            param_name="name", resource_field="display_name", is_mutable=True
        ),
        UpdateFieldSpec(param_name="network_firewall_policy_id", is_mutable=True),
        UpdateFieldSpec(
            param_name="network_security_group_ids",
            is_mutable=True,
            compare="sorted_list",
        ),
        UpdateFieldSpec(param_name="compartment_id", is_mutable=False),
        UpdateFieldSpec(param_name="subnet_id", is_mutable=False),
        UpdateFieldSpec(param_name="availability_domain", is_mutable=False),
        UpdateFieldSpec(param_name="ipv4_address", is_mutable=False),
        UpdateFieldSpec(param_name="ipv6_address", is_mutable=False),
    )

    def get_resource_response(self, resource_id):
        """Fetch the resource by OCID through the shared retry wrapper.

        Args:
            resource_id: The resource OCID.

        Returns:
            The OCI response containing the resource.
        """
        return self.call_with_retry(
            self.client.get_network_firewall,
            network_firewall_id=resource_id,
        )

    def hydrate_named_resource(self, resource):
        """Fetch the full firewall because list summaries omit NSG IDs.

        Args:
            resource: The resource summary returned by name lookup.

        Returns:
            The complete resource model.
        """
        return self.get_resource_by_id(resource.id)

    def create_resource(self):
        """Create the resource and apply the configured wait.

        Returns:
            The created resource model or its immediate snapshot.
        """
        response = self.call_with_retry(
            self.client.create_network_firewall,
            create_network_firewall_details=build_create_network_firewall_details(
                self.module.params
            ),
        )
        return self._wait_for_mutation(response, getattr(response.data, "id", None))

    def build_update_details(self, update_model_fields):
        """Build the OCI update model from planned fields.

        Args:
            update_model_fields: The fields selected by the update planner.

        Returns:
            The OCI update details model.
        """
        return oci.network_firewall.models.UpdateNetworkFirewallDetails(
            **update_model_fields
        )

    def _wait_for_mutation(self, response, resource_id, deleting=False):
        """Wait for a Network Firewall work request and return its resource.

        Args:
            response: OCI response returned by a mutation.
            resource_id: OCID of the affected firewall.
            deleting: Whether the mutation deletes the firewall.

        Returns:
            The refreshed resource, the immediate response data, or its OCID.
        """
        if not self.module.params.get("wait", True):
            return response.data or {"id": resource_id}
        work_request_id = getattr(response, "headers", {}).get("opc-work-request-id")
        if work_request_id:
            self.wait_for_work_request(self.client, work_request_id)
            if deleting:
                return response.data or {"id": resource_id}
            return self.get_resource_by_id(resource_id)
        return self.get_mutation_result(
            response.data,
            resource_id,
            tuple(self.dead_states) if deleting else WAIT_FOR_NETWORK_FIREWALL_STATES,
        )

    def update_resource(self, resource):
        """Apply the update plan and wait for its asynchronous operation.

        The inherited update method cannot wait for the returned work request.

        Args:
            resource: The current OCI resource model.

        Returns:
            The updated resource or its immediate snapshot.
        """
        update_plan = self.get_update_plan(resource)
        if not update_plan["update_model_fields"]:
            return resource
        response = self.call_with_retry(
            self.client.update_network_firewall,
            network_firewall_id=resource.id,
            update_network_firewall_details=self.build_update_details(
                update_plan["update_model_fields"]
            ),
        )
        return self._wait_for_mutation(response, resource.id)

    def delete_resource(self, resource):
        """Delete the resource and apply the configured wait.

        Args:
            resource: The OCI resource model to delete.

        Returns:
            The deletion response data or the result from the resource waiter.
        """
        response = self.call_delete_fn(
            resource,
            self.client.delete_network_firewall,
            network_firewall_id=resource.id,
        )
        return self._wait_for_mutation(response, resource.id, deleting=True)


def main():
    """Build the argument specification and execute the module."""
    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        network_firewall_id=dict(type="str"),
        network_firewall_policy_id=dict(type="str"),
        subnet_id=dict(type="str"),
        availability_domain=dict(type="str"),
        ipv4_address=dict(type="str"),
        ipv6_address=dict(type="str"),
        network_security_group_ids=dict(type="list", elements="str"),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    OciNetworkFirewallModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
