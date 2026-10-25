# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_network_loadbalancer_backend_info
short_description: Get OCI Network Load Balancer backend details
description:
  - Get one or more OCI Network Load Balancer backend resources.
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
  backend_set_name:
    description: The name of the parent backend set.
    type: str
    required: true
  name:
    description: The resource name. When omitted, the module lists resources.
    type: str
"""

EXAMPLES = r"""
- name: List Network Load Balancer backend resources
  ansible.oci.oci_network_loadbalancer_backend_info:
    network_load_balancer_id: ocid1.networkloadbalancer.oc1..example
    backend_set_name: application

- name: Get one Network Load Balancer backend
  ansible.oci.oci_network_loadbalancer_backend_info:
    network_load_balancer_id: ocid1.networkloadbalancer.oc1..example
    backend_set_name: application
    name: app-a
"""

RETURN = r"""
backends:
  description: Matching backend resources. A missing resource returns an empty list.
  returned: always
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
  sample:
  - name: app-a
    ip_address: 10.0.0.10
    target_id: null
    port: 8080
    weight: 2
    is_drain: false
    is_backup: false
    is_offline: false
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_network_loadbalancer import (
    OciNetworkLoadBalancerInfoBase,
)


class OciNetworkLoadBalancerBackendInfoModule(OciNetworkLoadBalancerInfoBase):
    """Read backend resources."""

    results_key = "backends"
    resource_id_param = "name"
    resource_id_kwarg = "backend_name"
    resource_get_method = "get_backend"
    list_resource_method = "list_backends"
    list_filter_params = ("network_load_balancer_id", "backend_set_name")
    name_response_field = "name"
    get_scope_params = ("network_load_balancer_id", "backend_set_name")


def main():
    """Initialize and run the backend info module."""
    spec = dict(OCI_AUTH_ARGS)
    spec.update(
        dict(
            network_load_balancer_id=dict(type="str", required=True),
            name=dict(type="str"),
        )
    )
    spec["backend_set_name"] = dict(type="str", required=True)
    module = AnsibleModule(argument_spec=spec, supports_check_mode=True)
    OciNetworkLoadBalancerBackendInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
