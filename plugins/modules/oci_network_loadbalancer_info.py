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
  description: Matching network load balancers. A missing resource returns an empty list.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The network load balancer OCID.
      type: str
    compartment_id:
      description: The compartment OCID.
      type: str
    name:
      description: The resource name.
      type: str
    lifecycle_state:
      description: The lifecycle state returned by OCI.
      type: str
    lifecycle_details:
      description: Additional information about the lifecycle state, when available.
      type: str
    ip_mode:
      description: The OCI IP version returned as C(ip_mode), such as C(IPV4) or C(IPV4_AND_IPV6).
      type: str
    time_created:
      description: The creation time in RFC 3339 format.
      type: str
    time_updated:
      description: The last update time in RFC 3339 format.
      type: str
    ip_addresses:
      description: The IP addresses assigned to the network load balancer.
      type: list
      elements: dict
      contains:
        ip_address:
          description: The IP address.
          type: str
        is_public:
          description: Whether the IP address is public.
          type: bool
        ip_version:
          description: The IP version used by the resource.
          type: str
        reserved_ip:
          description: The reserved public IP resource, when configured.
          type: dict
    is_private:
      description: Whether the network load balancer is private.
      type: bool
    is_preserve_source_destination:
      description: Whether the original source and destination addresses are preserved.
      type: bool
    is_symmetric_hash_enabled:
      description: Whether symmetric hashing is enabled.
      type: bool
    subnet_id:
      description: The subnet OCID.
      type: str
    network_security_group_ids:
      description: The OCIDs of the network security groups.
      type: list
      elements: str
    listeners:
      description: Listener configurations indexed by listener name.
      type: dict
    backend_sets:
      description: Backend set configurations indexed by backend set name.
      type: dict
    freeform_tags:
      description: The free-form tags.
      type: dict
    security_attributes:
      description: The security attributes grouped by namespace.
      type: dict
    defined_tags:
      description: The defined tags grouped by namespace.
      type: dict
    system_tags:
      description: The system tags assigned by OCI.
      type: dict
  sample:
  - id: ocid1.networkloadbalancer.oc1..example
    compartment_id: ocid1.compartment.oc1..example
    name: example-network-load-balancer
    lifecycle_state: ACTIVE
    lifecycle_details: null
    ip_mode: IPV4
    time_created: '2026-10-21T14:48:00Z'
    time_updated: '2026-10-21T14:48:00Z'
    ip_addresses:
    - ip_address: 192.0.2.10
      is_public: true
      ip_version: IPV4
      reserved_ip: null
    is_private: false
    is_preserve_source_destination: false
    is_symmetric_hash_enabled: false
    subnet_id: ocid1.subnet.oc1..example
    network_security_group_ids: []
    listeners:
      application:
        name: application
        default_backend_set_name: application
        port: 8080
        protocol: TCP
        ip_version: IPV4
        is_ppv2_enabled: false
        tcp_idle_timeout: 360
        udp_idle_timeout: 120
        l3_ip_idle_timeout: 120
    backend_sets:
      application:
        name: application
        policy: FIVE_TUPLE
        is_preserve_source: true
        is_fail_open: false
        is_instant_failover_enabled: false
        is_instant_failover_tcp_reset_enabled: false
        are_operationally_active_backends_preferred: false
        ip_version: IPV4
        backends:
        - name: app-a
          ip_address: 10.0.0.10
          target_id: null
          port: 8080
          weight: 2
          is_drain: false
          is_backup: false
          is_offline: false
        health_checker:
          protocol: TCP
          port: 8080
          retries: 3
          timeout_in_millis: 1000
          interval_in_millis: 10000
          url_path: null
          response_body_regex: null
          return_code: null
          request_data: null
          response_data: null
          dns: null
    freeform_tags:
      phase: create
    security_attributes: {}
    defined_tags: {}
    system_tags: {}
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
