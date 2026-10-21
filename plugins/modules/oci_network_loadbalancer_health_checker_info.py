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
  description: Matching health checker resources.
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
