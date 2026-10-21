# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_network_loadbalancer_info
short_description: Retrieve OCI network load balancer information
description: Retrieve one network load balancer or list resources in a compartment.
version_added: "1.2.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_info_filter_options
options:
  network_load_balancer_id:
    description: Network load balancer OCID.
    type: str
  compartment_id:
    description: Compartment OCID for list operations.
    type: str
  name:
    description: Filter resources by display name.
    type: str
  lifecycle_state:
    description: Filter resources by lifecycle state.
    type: str
    choices: [creating, updating, failed, active, deleting, deleted]
"""

EXAMPLES = r"""
- name: List active network load balancers
  ansible.oci.oci_network_loadbalancer_info:
    compartment_id: ocid1.compartment.oc1..example
    lifecycle_state: active

- name: Get a network load balancer by OCID
  ansible.oci.oci_network_loadbalancer_info:
    network_load_balancer_id: ocid1.networkloadbalancer.oc1..example
"""

RETURN = r"""
network_load_balancers:
  description: Matching network load balancers with display name as C(name) and IP version as C(ip_mode).
  returned: always
  type: list
  elements: dict
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_network_loadbalancer import (
    OciNetworkLoadBalancerInfoBase,
)


class OciNetworkLoadBalancerInfoModule(OciNetworkLoadBalancerInfoBase):
    """Retrieve OCI network load balancers."""

    results_key = "network_load_balancers"
    resource_id_param = "network_load_balancer_id"
    resource_get_method = "get_network_load_balancer"
    list_resource_method = "list_network_load_balancers"
    list_filter_params = ("compartment_id", "lifecycle_state")
    field_param_aliases = {"nlb_ip_version": "ip_mode"}

    def collect_list_filters(self, *param_groups):
        """Convert the lifecycle filter to the SDK enum spelling.

        Args:
            *param_groups: Parameter groups to collect.

        Returns:
            SDK list filters with an uppercase lifecycle state.
        """
        filters = super(OciNetworkLoadBalancerInfoModule, self).collect_list_filters(
            *param_groups
        )
        if "lifecycle_state" in filters:
            filters["lifecycle_state"] = filters["lifecycle_state"].upper()
        return filters


def main():
    """Build the argument spec and run the info module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        network_load_balancer_id=dict(type="str"),
        compartment_id=dict(type="str"),
        name=dict(type="str"),
        lifecycle_state=dict(
            type="str",
            choices=["creating", "updating", "failed", "active", "deleting", "deleted"],
        ),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        required_one_of=[["network_load_balancer_id", "compartment_id"]],
        supports_check_mode=True,
    )
    OciNetworkLoadBalancerInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
