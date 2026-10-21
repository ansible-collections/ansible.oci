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
"""

RETURN = r"""
backends:
  description: Matching backend resources.
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
