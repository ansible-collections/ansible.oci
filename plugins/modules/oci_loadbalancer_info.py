# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_loadbalancer_info
short_description: Retrieve load balancer information from OCI
description: >-
  Retrieve one load balancer or list load balancers in a compartment.
version_added: "1.2.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_info_filter_options
options:
  load_balancer_id:
    description:
      - The OCID of one load balancer to retrieve.
      - Use C(id) as an alias.
    type: str
    aliases: [id]
  compartment_id:
    description:
      - The OCID of the compartment to list load balancers from.
    type: str
  name:
    description:
      - Filter load balancers by display name.
      - Only used when C(compartment_id) is provided.
      - Use C(display_name) as an alias.
    type: str
    aliases: [display_name]
"""

EXAMPLES = r"""
- name: List active load balancers in a compartment
  ansible.oci.oci_loadbalancer_info:
    compartment_id: ocid1.compartment.oc1..example
    lifecycle_state: ACTIVE

- name: Get a load balancer by OCID
  ansible.oci.oci_loadbalancer_info:
    load_balancer_id: ocid1.loadbalancer.oc1..example
"""

RETURN = r"""
load_balancers:
  description: Load balancers that matched the query, with OCI display names returned as C(name).
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The OCID of the load balancer.
      type: str
      returned: when available
    name:
      description: The display name of the load balancer, returned as name.
      type: str
      returned: when available
    compartment_id:
      description: The OCID of the containing compartment.
      type: str
      returned: when available
    lifecycle_state:
      description: The current lifecycle state of the load balancer.
      type: str
      returned: when available
    shape_name:
      description: The OCI shape name, such as flexible.
      type: str
      returned: when available
    shape_details:
      description: The bandwidth configuration of a flexible load balancer.
      type: dict
      returned: when available
      contains:
        minimum_bandwidth_in_mbps:
          description: The minimum bandwidth in Mbps.
          type: int
          returned: when available
        maximum_bandwidth_in_mbps:
          description: The maximum bandwidth in Mbps.
          type: int
          returned: when available
    ip_mode:
      description: The IP mode returned by OCI as IPV4 or IPV6.
      type: str
      returned: when available
    is_private:
      description: Whether the load balancer has a private IP address.
      type: bool
      returned: when available
    ip_addresses:
      description: The IP addresses assigned to the load balancer.
      type: list
      returned: when available
      elements: dict
      contains:
        ip_address:
          description: The allocated IP address.
          type: str
          returned: when available
        is_public:
          description: Whether the IP address is public.
          type: bool
          returned: when available
        reserved_ip:
          description: The reserved public IP reference, or null when no reserved IP is attached.
          type: dict
          returned: when available
          contains:
            id:
              description: The OCID of the reserved public IP.
              type: str
              returned: when a reserved IP is attached
    subnet_ids:
      description: The OCIDs of the subnets used by the load balancer.
      type: list
      returned: when available
      elements: str
    network_security_group_ids:
      description: The OCIDs of the associated network security groups.
      type: list
      returned: when available
      elements: str
    is_delete_protection_enabled:
      description: Whether deletion protection is enabled. May be null when unset.
      type: bool
      returned: when available
    is_request_id_enabled:
      description: Whether request IDs are enabled. May be null when unset.
      type: bool
      returned: when available
    request_id_header:
      description: The request ID header name. May be null when unset.
      type: str
      returned: when available
    backend_sets:
      description: Backend set configurations keyed by name.
      type: dict
      returned: when available
    listeners:
      description: Listener configurations keyed by name.
      type: dict
      returned: when available
    certificates:
      description: Certificate configurations keyed by name.
      type: dict
      returned: when available
    hostnames:
      description: Hostname configurations keyed by name.
      type: dict
      returned: when available
    path_route_sets:
      description: Path route set configurations keyed by name.
      type: dict
      returned: when available
    routing_policies:
      description: Routing policy configurations keyed by name.
      type: dict
      returned: when available
    rule_sets:
      description: Rule set configurations keyed by name.
      type: dict
      returned: when available
    ssl_cipher_suites:
      description: SSL cipher suite configurations keyed by name.
      type: dict
      returned: when available
    freeform_tags:
      description: Free-form tags applied to the load balancer.
      type: dict
      returned: when available
    defined_tags:
      description: Defined tags applied to the load balancer.
      type: dict
      returned: when available
    system_tags:
      description: System tags returned by OCI.
      type: dict
      returned: when available
    security_attributes:
      description: Security attributes returned by OCI.
      type: dict
      returned: when available
    time_created:
      description: The date and time the load balancer was created.
      type: str
      returned: when available
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import OciInfoBase

oci = import_oci_sdk()[0]


class OciLoadBalancerInfoModule(OciInfoBase):
    """Concrete info adapter for OCI load balancers."""

    @property
    def client_class(self):
        """Return the load-balancer service client required by this adapter."""
        return oci.load_balancer.LoadBalancerClient

    results_key = "load_balancers"
    resource_id_param = "load_balancer_id"
    resource_get_method = "get_load_balancer"
    list_resource_method = "list_load_balancers"
    list_filter_params = ("compartment_id", "lifecycle_state")


def main():
    """Build the info argument spec and run the load-balancer info module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        load_balancer_id=dict(type="str", aliases=["id"]),
        compartment_id=dict(type="str"),
        name=dict(type="str", aliases=["display_name"]),
        lifecycle_state=dict(type="str"),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["load_balancer_id", "compartment_id"]],
    )
    OciLoadBalancerInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
