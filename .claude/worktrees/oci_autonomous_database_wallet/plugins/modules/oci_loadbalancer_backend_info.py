# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_loadbalancer_backend_info
short_description: Retrieve backend server information from an OCI load balancer
description:
  - Retrieve one backend server or list backend servers in a load balancer backend set.
version_added: "1.2.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  load_balancer_id:
    description:
      - The OCID of the load balancer containing the backend set.
    type: str
    required: true
  backend_set_name:
    description:
      - The name of the backend set to query.
    type: str
    required: true
  name:
    description:
      - The backend identifier in C(ip_address:port) form.
      - When supplied, retrieve only that backend server.
    type: str
"""

EXAMPLES = r"""
- name: List backend servers in a backend set
  ansible.oci.oci_loadbalancer_backend_info:
    load_balancer_id: ocid1.loadbalancer.oc1..example
    backend_set_name: app_pool

- name: Retrieve one backend server
  ansible.oci.oci_loadbalancer_backend_info:
    load_balancer_id: ocid1.loadbalancer.oc1..example
    backend_set_name: app_pool
    name: 10.0.0.7:8080
"""

RETURN = r"""
backends:
  description: Backend servers that matched the query. A missing requested backend returns an empty list.
  returned: always
  type: list
  elements: dict
  contains:
    ip_address:
      description: The backend server IP address.
      type: str
      sample: 10.0.0.7
    port:
      description: The backend server port.
      type: int
      sample: 8080
    weight:
      description: The backend server's load balancing weight.
      type: int
      sample: 3
    backup:
      description: Whether this backend is a backup server.
      type: bool
      sample: false
    drain:
      description: Whether this backend is draining.
      type: bool
      sample: false
    offline:
      description: Whether this backend is offline.
      type: bool
      sample: false
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_base import oci
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import OciInfoBase


class OciLoadBalancerBackendInfoModule(OciInfoBase):
    """Read one backend server or list servers in a backend set."""

    @property
    def client_class(self):
        """Return the load balancer SDK client.

        Returns:
            The LoadBalancerClient class.
        """
        return oci.load_balancer.LoadBalancerClient

    results_key = "backends"

    def fetch_resources(self):
        """Fetch the named backend or list all backends.

        Returns:
            The matching SDK models, or an empty list when missing.
        """
        load_balancer_id = self.module.params.get("load_balancer_id")
        backend_set_name = self.module.params.get("backend_set_name")
        backend_name = self.module.params.get("name")
        if backend_name:
            return self.get_resource_by_id(
                backend_name,
                self.client.get_backend,
                load_balancer_id=load_balancer_id,
                backend_set_name=backend_set_name,
                backend_name=backend_name,
            )
        try:
            return self.list_all_resources(
                self.client.list_backends,
                load_balancer_id=load_balancer_id,
                backend_set_name=backend_set_name,
            )
        except Exception as exc:
            if getattr(exc, "status", None) == 404:
                return []
            raise


def main():
    """Initialize and run the backend info module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        load_balancer_id=dict(type="str", required=True),
        backend_set_name=dict(type="str", required=True),
        name=dict(type="str"),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    OciLoadBalancerBackendInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
