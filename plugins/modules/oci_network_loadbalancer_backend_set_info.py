# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_network_loadbalancer_backend_set_info
short_description: Get OCI Network Load Balancer backend set details
description:
  - Get one or more OCI Network Load Balancer backend set resources.
version_added: "1.2.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  network_load_balancer_id:
    description: The OCID of the network load balancer.
    type: str
    required: true
  name:
    description: The resource name. When omitted, the module lists resources.
    type: str
"""

EXAMPLES = r"""
- name: List Network Load Balancer backend set resources
  ansible.oci.oci_network_loadbalancer_backend_set_info:
    network_load_balancer_id: ocid1.networkloadbalancer.oc1..example

- name: Get one Network Load Balancer backend set
  ansible.oci.oci_network_loadbalancer_backend_set_info:
    network_load_balancer_id: ocid1.networkloadbalancer.oc1..example
    name: application
"""

RETURN = r"""
backend_sets:
  description: Matching backend sets. A missing resource returns an empty list.
  returned: always
  type: list
  elements: dict
  contains:
    name:
      description: The resource name.
      type: str
    policy:
      description: The packet fields used to select a backend.
      type: str
    is_preserve_source:
      description: Whether backends receive the original source IP address.
      type: bool
    is_fail_open:
      description: Whether traffic continues when all backends are unhealthy.
      type: bool
    is_instant_failover_enabled:
      description: Whether existing connections move when their backend becomes unhealthy.
      type: bool
    is_instant_failover_tcp_reset_enabled:
      description: Whether TCP resets are sent during instant failover.
      type: bool
    are_operationally_active_backends_preferred:
      description: Whether the active backend remains preferred after the previous backend recovers.
      type: bool
    ip_version:
      description: The IP version used by the resource.
      type: str
    backends:
      description: The backend servers in the backend set.
      type: list
      elements: dict
      contains:
        name:
          description: The resource name.
          type: str
        ip_address:
          description: The IP address.
          type: str
        target_id:
          description: The OCID of the backend target, when configured.
          type: str
        port:
          description: The configured port.
          type: int
        weight:
          description: The weight used to distribute traffic to the backend.
          type: int
        is_drain:
          description: Whether the backend stops receiving new connections.
          type: bool
        is_backup:
          description: Whether the backend serves as a backup.
          type: bool
        is_offline:
          description: Whether the backend stops receiving traffic.
          type: bool
    health_checker:
      description: The health check configuration for the backend set.
      type: dict
      contains:
        protocol:
          description: The configured protocol.
          type: str
        port:
          description: The configured port.
          type: int
        retries:
          description: The number of retries before a backend changes health state.
          type: int
        timeout_in_millis:
          description: The response timeout for each health check in milliseconds.
          type: int
        interval_in_millis:
          description: The interval between health checks in milliseconds.
          type: int
        url_path:
          description: The URL path requested by HTTP health checks.
          type: str
        response_body_regex:
          description: The regular expression used to check an HTTP response body.
          type: str
        return_code:
          description: The HTTP response code that indicates a healthy backend.
          type: int
        request_data:
          description: The base64-encoded request data for TCP or UDP health checks.
          type: str
        response_data:
          description: The base64-encoded response data for TCP or UDP health checks.
          type: str
        dns:
          description: The DNS health check configuration.
          type: dict
          contains:
            transport_protocol:
              description: The transport protocol for DNS queries.
              type: str
            domain_name:
              description: The domain name queried by the health check.
              type: str
            query_class:
              description: The DNS query class, either C(IN) or C(CH).
              type: str
            query_type:
              description: The DNS record type queried by the health check.
              type: str
            rcodes:
              description: The DNS response codes that indicate a healthy backend.
              type: list
              elements: str
  sample:
  - name: application
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
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_network_loadbalancer import (
    OciNetworkLoadBalancerInfoBase,
)


class OciNetworkLoadBalancerBackendSetInfoModule(OciNetworkLoadBalancerInfoBase):
    """Read backend set resources."""

    results_key = "backend_sets"
    resource_id_param = "name"
    resource_id_kwarg = "backend_set_name"
    resource_get_method = "get_backend_set"
    list_resource_method = "list_backend_sets"
    list_filter_params = ("network_load_balancer_id",)
    name_response_field = "name"
    get_scope_params = ("network_load_balancer_id",)


def main():
    """Initialize and run the backend set info module."""
    spec = dict(OCI_AUTH_ARGS)
    spec.update(
        dict(
            network_load_balancer_id=dict(type="str", required=True),
            name=dict(type="str"),
        )
    )
    module = AnsibleModule(argument_spec=spec, supports_check_mode=True)
    OciNetworkLoadBalancerBackendSetInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
