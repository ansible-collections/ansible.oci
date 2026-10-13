# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_loadbalancer_listener_info
short_description: Get listeners from an OCI Load Balancer
description:
  - Get all listeners for a Load Balancer, or select one by name.
version_added: "1.2.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  load_balancer_id:
    description:
      - OCID of the Load Balancer whose listeners are returned.
    type: str
    required: true
  name:
    description:
      - If supplied, return only the listener with this name.
    type: str
"""

EXAMPLES = r"""
- name: List listeners on a Load Balancer
  ansible.oci.oci_loadbalancer_listener_info:
    load_balancer_id: ocid1.loadbalancer.oc1..example
  register: listener_results

- name: Get one listener by name
  ansible.oci.oci_loadbalancer_listener_info:
    load_balancer_id: ocid1.loadbalancer.oc1..example
    name: web-listener
"""

RETURN = r"""
listeners:
  description: List of listeners on the requested Load Balancer.
  returned: always
  type: list
  elements: dict
  contains:
    name:
      description: Listener name.
      type: str
      returned: always
    default_backend_set_name:
      description: Associated backend set name.
      type: str
      returned: always
    port:
      description: Listener port.
      type: int
      returned: always
    protocol:
      description: Listener protocol.
      type: str
      returned: always
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    filter_resources_by_response_field,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import OciInfoBase

oci = import_oci_sdk()[0]


class OciLoadBalancerListenerInfoModule(OciInfoBase):
    """Read listeners from a Load Balancer parent resource."""

    @property
    def client_class(self):
        """Return the load balancer SDK client.

        Returns:
            The LoadBalancerClient class.
        """
        return oci.load_balancer.LoadBalancerClient

    results_key = "listeners"

    def fetch_resources(self):
        """Fetch the named listener or list all listeners.

        Returns:
            The matching SDK models, or an empty list when missing.
        """
        try:
            response = self.call_with_retry(
                self.client.get_load_balancer,
                load_balancer_id=self.module.params["load_balancer_id"],
            )
        except oci.exceptions.ServiceError as exc:
            if exc.status == 404:
                return []
            raise

        listeners = getattr(response.data, "listeners", None) or {}
        resources = sorted(
            listeners.values(),
            key=lambda listener: getattr(listener, "name", ""),
        )
        return filter_resources_by_response_field(
            resources, "name", self.module.params.get("name")
        )


def main():
    """Initialize and run the listener info module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        load_balancer_id=dict(type="str", required=True),
        name=dict(type="str"),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    OciLoadBalancerListenerInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
