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
from ansible_collections.ansible.oci.plugins.module_utils.oci_loadbalancer import (
    OciLoadBalancerInfoBase,
)


class OciLoadBalancerBackendSetInfoModule(OciLoadBalancerInfoBase):
    """Read one backend set or list backend sets for a load balancer."""

    results_key = "backend_sets"
    resource_id_param = "name"
    resource_id_kwarg = "backend_set_name"
    resource_get_method = "get_backend_set"
    name_response_field = "name"
    get_scope_params = ("load_balancer_id",)
    list_resource_method = "list_backend_sets"
    list_filter_params = ("load_balancer_id",)


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
