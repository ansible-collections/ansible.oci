# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_loadbalancer_routing_policy_info
short_description: Get routing policies from an OCI Load Balancer
description:
  - Get all routing policies for a Load Balancer, or select one by name.
version_added: "1.2.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  load_balancer_id:
    description: OCID of the Load Balancer to query.
    type: str
    required: true
  name:
    description: Name of one routing policy to return. If omitted, return all policies.
    type: str
"""

EXAMPLES = r"""
- name: List routing policies
  ansible.oci.oci_loadbalancer_routing_policy_info:
    load_balancer_id: ocid1.loadbalancer.oc1..example

- name: Get one routing policy
  ansible.oci.oci_loadbalancer_routing_policy_info:
    load_balancer_id: ocid1.loadbalancer.oc1..example
    name: image_routing
"""

RETURN = r"""
routing_policies:
  description: Routing policies that match the query. A missing named policy returns an empty list.
  returned: always
  type: list
  elements: dict
  contains:
    name:
      description: Routing policy name.
      type: str
    condition_language_version:
      description: Condition language version.
      type: str
    rules:
      description: Ordered routing rules.
      type: list
      elements: dict
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import OCI_AUTH_ARGS
from ansible_collections.ansible.oci.plugins.module_utils.oci_loadbalancer import (
    OciLoadBalancerInfoBase,
)


class OciLoadBalancerRoutingPolicyInfoModule(OciLoadBalancerInfoBase):
    """Read routing policies from a Load Balancer."""

    results_key = "routing_policies"
    resource_id_param = "name"
    resource_id_kwarg = "routing_policy_name"
    resource_get_method = "get_routing_policy"
    name_response_field = "name"
    get_scope_params = ("load_balancer_id",)
    list_resource_method = "list_routing_policies"
    list_filter_params = ("load_balancer_id",)


def main():
    """Initialize and run the routing policy info module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        load_balancer_id=dict(type="str", required=True),
        name=dict(type="str"),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    OciLoadBalancerRoutingPolicyInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
