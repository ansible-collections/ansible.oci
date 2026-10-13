# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_loadbalancer_health_checker_info
short_description: Get the health checker for an OCI Load Balancer backend set
description:
  - Get health-check settings for a backend set.
version_added: "1.2.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  load_balancer_id:
    description:
      - OCID of the Load Balancer containing the backend set.
    type: str
    required: true
  name:
    description:
      - Name of the backend set whose health checker is returned.
    type: str
    required: true
"""

EXAMPLES = r"""
- name: Get a backend set health checker
  ansible.oci.oci_loadbalancer_health_checker_info:
    load_balancer_id: ocid1.loadbalancer.oc1..example
    name: app-backends
  register: health_checker_results
"""

RETURN = r"""
health_checkers:
  description: A one-element list containing the health checker, or an empty list when it is not found.
  returned: always
  type: list
  elements: dict
  contains:
    protocol:
      description: Health check protocol.
      type: str
      returned: always
    url_path:
      description: HTTP health-check path.
      type: str
      returned: when set
    port:
      description: Backend server port.
      type: int
      returned: always
    return_code:
      description: Expected healthy HTTP status code.
      type: int
      returned: always
    retries:
      description: Retry count.
      type: int
      returned: always
    timeout_in_millis:
      description: Response timeout in milliseconds.
      type: int
      returned: always
    interval_in_millis:
      description: Interval between checks in milliseconds.
      type: int
      returned: always
    response_body_regex:
      description: Response body regular expression.
      type: str
      returned: always
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import OciInfoBase

oci = import_oci_sdk()[0]


class OciLoadBalancerHealthCheckerInfoModule(OciInfoBase):
    """Read a health checker using its Load Balancer and backend set scope."""

    @property
    def client_class(self):
        """Return the load balancer SDK client.

        Returns:
            The LoadBalancerClient class.
        """
        return oci.load_balancer.LoadBalancerClient

    results_key = "health_checkers"

    def fetch_resources(self):
        """Fetch the backend set health checker.

        Returns:
            The matching SDK models, or an empty list when missing.
        """
        return self.get_resource_by_id(
            self.module.params["name"],
            self.client.get_health_checker,
            load_balancer_id=self.module.params["load_balancer_id"],
            backend_set_name=self.module.params["name"],
        )


def main():
    """Initialize and run the health checker info module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        load_balancer_id=dict(type="str", required=True),
        name=dict(type="str", required=True),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    OciLoadBalancerHealthCheckerInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
