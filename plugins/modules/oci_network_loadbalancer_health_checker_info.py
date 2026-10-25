# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_network_loadbalancer_health_checker_info
short_description: Get OCI Network Load Balancer health checker details
description:
  - Get the health checker for one backend set.
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
    description: The backend set name.
    type: str
    required: true
"""

EXAMPLES = r"""
- name: Get the health checker for a backend set
  ansible.oci.oci_network_loadbalancer_health_checker_info:
    network_load_balancer_id: ocid1.networkloadbalancer.oc1..example
    name: application
"""

RETURN = r"""
health_checkers:
  description: Matching health checkers. A missing resource returns an empty list.
  returned: always
  type: list
  elements: dict
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
  - protocol: DNS
    port: 53
    retries: 3
    timeout_in_millis: 1000
    interval_in_millis: 10000
    url_path: null
    response_body_regex: null
    return_code: null
    request_data: null
    response_data: null
    dns:
      transport_protocol: UDP
      domain_name: example.com
      query_class: IN
      query_type: A
      rcodes:
      - NOERROR
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_network_loadbalancer import (
    OciNetworkLoadBalancerInfoBase,
)


class OciNetworkLoadBalancerHealthCheckerInfoModule(OciNetworkLoadBalancerInfoBase):
    """Read the health checker for one backend set."""

    results_key = "health_checkers"
    resource_id_param = "name"
    resource_id_kwarg = "backend_set_name"
    resource_get_method = "get_health_checker"
    get_scope_params = ("network_load_balancer_id",)


def main():
    """Initialize and run the health checker info module."""
    spec = dict(OCI_AUTH_ARGS)
    spec.update(
        dict(
            network_load_balancer_id=dict(type="str", required=True),
            name=dict(type="str", required=True),
        )
    )
    module = AnsibleModule(argument_spec=spec, supports_check_mode=True)
    OciNetworkLoadBalancerHealthCheckerInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
