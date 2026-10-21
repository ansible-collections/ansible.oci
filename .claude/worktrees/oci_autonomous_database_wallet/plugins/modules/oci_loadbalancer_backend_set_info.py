# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_loadbalancer_backend_set_info
short_description: Retrieve backend set information from an OCI load balancer
description:
  - Retrieve one backend set or list backend sets configured on an OCI load balancer.
version_added: "1.2.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  load_balancer_id:
    description:
      - The OCID of the load balancer to query.
    type: str
    required: true
  name:
    description:
      - The backend set name to retrieve.
      - When omitted, all backend sets for C(load_balancer_id) are listed.
    type: str
"""

EXAMPLES = r"""
- name: List backend sets
  ansible.oci.oci_loadbalancer_backend_set_info:
    load_balancer_id: ocid1.loadbalancer.oc1..example

- name: Retrieve one backend set
  ansible.oci.oci_loadbalancer_backend_set_info:
    load_balancer_id: ocid1.loadbalancer.oc1..example
    name: app_pool
"""

RETURN = r"""
backend_sets:
  description: Backend sets matching the query. A missing named backend set returns an empty list.
  returned: always
  type: list
  elements: dict
  contains:
    name:
      description: The backend set name.
      type: str
      sample: app_pool
    policy:
      description: The load balancing policy.
      type: str
      sample: ROUND_ROBIN
    backends:
      description: Backend servers configured for the set.
      type: list
      elements: dict
    health_checker:
      description: Health check settings for the set.
      type: dict
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_base import oci
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import OciInfoBase


class OciLoadBalancerBackendSetInfoModule(OciInfoBase):
    """Read one backend set or list backend sets for a load balancer."""

    @property
    def client_class(self):
        """Return the load balancer SDK client.

        Returns:
            The LoadBalancerClient class.
        """
        return oci.load_balancer.LoadBalancerClient

    results_key = "backend_sets"

    def fetch_resources(self):
        """Fetch the named backend set or list all backend sets.

        Returns:
            The matching SDK models, or an empty list when missing.
        """
        load_balancer_id = self.module.params.get("load_balancer_id")
        backend_set_name = self.module.params.get("name")
        if backend_set_name:
            return self.get_resource_by_id(
                backend_set_name,
                self.client.get_backend_set,
                load_balancer_id=load_balancer_id,
                backend_set_name=backend_set_name,
            )
        try:
            return self.list_all_resources(
                self.client.list_backend_sets,
                load_balancer_id=load_balancer_id,
            )
        except Exception as exc:
            if getattr(exc, "status", None) == 404:
                return []
            raise


def main():
    """Initialize and run the backend set info module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        load_balancer_id=dict(type="str", required=True),
        name=dict(type="str"),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    OciLoadBalancerBackendSetInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
