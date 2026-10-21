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
from ansible_collections.ansible.oci.plugins.module_utils.oci_base import oci
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import OciInfoBase


class OciLoadBalancerRoutingPolicyInfoModule(OciInfoBase):
    """Read routing policies from a Load Balancer."""

    @property
    def client_class(self):
        """Return the Load Balancer SDK client.

        Returns:
            The LoadBalancerClient class.
        """
        return oci.load_balancer.LoadBalancerClient

    results_key = "routing_policies"

    def fetch_resources(self):
        """Fetch the named policy or list policies for a Load Balancer.

        This override passes the parent OCID to the named getter. The inherited
        metadata path cannot add this required argument.

        Returns:
            Matching SDK models, or an empty list when the policy is missing.

        Raises:
            oci.exceptions.ServiceError: If OCI returns an error other than 404.
        """
        load_balancer_id = self.module.params.get("load_balancer_id")
        routing_policy_name = self.module.params.get("name")
        if routing_policy_name:
            return self.get_resource_by_id(
                routing_policy_name,
                self.client.get_routing_policy,
                load_balancer_id=load_balancer_id,
                routing_policy_name=routing_policy_name,
            )
        try:
            return self.list_all_resources(
                self.client.list_routing_policies,
                load_balancer_id=load_balancer_id,
            )
        except Exception as exc:
            if getattr(exc, "status", None) == 404:
                return []
            raise


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
