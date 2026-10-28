# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = r"""
---
module: oci_network_firewall_info
short_description: Retrieve OCI Network Firewall information
description:
  - Retrieve OCI Network Firewall information.
version_added: 1.2.0
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_info_filter_options
options:
  compartment_id:
    description:
      - The OCID of the compartment that contains the resource.
      - Required when listing resources.
    type: str
  network_firewall_id:
    description: The OCID of one firewall. This option returns full resource details.
    type: str
  name:
    description:
      - Filter listed resources by exact display name. This filter applies only when compartment_id is set.
    type: str
  lifecycle_state:
    description: Filter by lifecycle state.
    type: str
    choices:
      - creating
      - updating
      - active
      - deleting
      - deleted
      - failed
      - needs_attention
"""

EXAMPLES = r"""
- name: List Network Firewalls
  ansible.oci.oci_network_firewall_info:
    compartment_id: ocid1.compartment.oc1..example

- name: Get one Network Firewall with full details
  ansible.oci.oci_network_firewall_info:
    network_firewall_id: ocid1.networkfirewall.oc1..example
"""

RETURN = r"""
network_firewalls:
  description: >-
    Matching Network Firewalls. An OCID lookup returns full details. A list query returns summary
    details.
  returned: always
  type: list
  elements: dict
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
      description: Network Security Group OCIDs. This field can be absent in list summaries.
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
    - id: ocid1.networkfirewall.oc1..example
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
      time_created: '2026-01-01T00:00:00+00:00'
      time_updated: '2026-01-01T00:00:00+00:00'
      lifecycle_state: ACTIVE
      lifecycle_details: null
      network_security_group_ids: []
      freeform_tags: {}
      defined_tags: {}
      system_tags: {}
      security_attributes: {}
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import OciInfoBase

imported_oci_sdk = import_oci_sdk()
oci = imported_oci_sdk[0]
LIFECYCLE_STATES = {
    "creating": "CREATING",
    "updating": "UPDATING",
    "active": "ACTIVE",
    "deleting": "DELETING",
    "deleted": "DELETED",
    "failed": "FAILED",
    "needs_attention": "NEEDS_ATTENTION",
}


class OciNetworkFirewallInfoModule(OciInfoBase):
    """Retrieve OCI Network Firewalls."""

    @property
    def client_class(self):
        """Return the OCI service client class.

        Returns:
            The OCI service client class.
        """
        return oci.network_firewall.NetworkFirewallClient

    results_key = "network_firewalls"
    resource_id_param = "network_firewall_id"
    resource_get_method = "get_network_firewall"
    list_resource_method = "list_network_firewalls"
    list_filter_params = ["compartment_id", "lifecycle_state"]

    def collect_list_filters(self, *param_groups):
        """Collect list filters and map lifecycle state to OCI casing.

        Args:
            *param_groups: Parameter groups accepted by the shared helper.

        Returns:
            A dictionary of OCI list query parameters.
        """
        filters = super().collect_list_filters(*param_groups)
        if "lifecycle_state" in filters:
            filters["lifecycle_state"] = LIFECYCLE_STATES[filters["lifecycle_state"]]
        return filters


def main():
    """Build the argument specification and execute the module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        compartment_id=dict(type="str"),
        network_firewall_id=dict(type="str"),
        name=dict(type="str"),
        lifecycle_state=dict(type="str", choices=list(LIFECYCLE_STATES)),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["compartment_id", "network_firewall_id"]],
    )
    OciNetworkFirewallInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
