# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: oci_network_loadbalancer_listener
short_description: Manage an OCI Network Load Balancer listener
description:
- Create, update, or delete an OCI Network Load Balancer listener.
version_added: 1.2.0
author:
- Ron Gershburg (@ronger4)
extends_documentation_fragment:
- ansible.oci.oci_auth_options
- ansible.oci.oci_wait_options
options:
  network_load_balancer_id:
    description: The OCID of the network load balancer.
    type: str
    required: true
  name:
    description: The listener name.
    type: str
    required: true
  default_backend_set_name:
    description: Default backend set for incoming traffic. Required when creating a listener.
    type: str
  port:
    description: Port that accepts incoming traffic. Required when creating a listener.
    type: int
  protocol:
    description:
    - Protocol accepted by the listener. Required when creating a listener.
    - Currently supported protocols are C(any), C(tcp), C(udp), C(tcp_and_udp), and C(l3ip).
    - See Oracle's documentation for the latest supported protocols at
      U(https://docs.oracle.com/en-us/iaas/tools/python/latest/api/network_load_balancer/models/oci.network_load_balancer.models.CreateListenerDetails.html).
    type: str
  ip_version:
    description:
    - IP version used by this listener.
    - Each listener and its backend set must use the same IP version.
    - For a parent with both IP versions, create separate IPv4 and IPv6 listeners and backend sets.
    - See U(https://docs.oracle.com/en-us/iaas/Content/NetworkLoadBalancer/NetworkLoadBalancers/create-network-load-balancer.htm).
    type: str
    choices:
    - ipv4
    - ipv6
  is_ppv2_enabled:
    description: Whether to enable Proxy Protocol version 2 for this listener.
    type: bool
  tcp_idle_timeout:
    description: Maximum idle time in seconds for TCP connections.
    type: int
  udp_idle_timeout:
    description: Maximum idle time in seconds for UDP connections.
    type: int
  l3_ip_idle_timeout:
    description: Maximum idle time in seconds for L3IP connections.
    type: int
  wait:
    description: Whether to wait for the work request to complete.
    type: bool
    default: true
  state:
    description: The desired resource state.
    type: str
    choices:
    - present
    - absent
    default: present
"""

EXAMPLES = r"""
- name: Create a TCP listener
  ansible.oci.oci_network_loadbalancer_listener:
    network_load_balancer_id: ocid1.networkloadbalancer.oc1..example
    name: application
    default_backend_set_name: application
    port: 8080
    protocol: tcp

- name: Change the listener port
  ansible.oci.oci_network_loadbalancer_listener:
    network_load_balancer_id: ocid1.networkloadbalancer.oc1..example
    name: application
    port: 8081

- name: Create listeners for existing backend sets with matching IP versions
  ansible.oci.oci_network_loadbalancer_listener:
    network_load_balancer_id: ocid1.networkloadbalancer.oc1..example
    name: "application-{{ item }}"
    default_backend_set_name: "application-{{ item }}"
    ip_version: "{{ item }}"
    port: 8080
    protocol: tcp
  loop:
    - ipv4
    - ipv6
"""

RETURN = r"""
resource:
  description: The listener after the operation.
  returned: when state is present
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    OCI_WAIT_ARGS,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    UpdateFieldSpec,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_network_loadbalancer import (
    OciNetworkLoadBalancerSubresourceBase,
)


class OciNetworkLoadBalancerListenerModule(OciNetworkLoadBalancerSubresourceBase):
    """Manage one listener."""

    create_model_name = "CreateListenerDetails"
    create_method_name = "create_listener"
    create_details_name = "create_listener_details"
    update_model_name = "UpdateListenerDetails"
    update_method_name = "update_listener"
    update_details_name = "update_listener_details"
    delete_method_name = "delete_listener"
    create_resource_name = "listener"

    def get_resource_response(self, resource_id):
        """Read one child resource from OCI.

        Args:
            resource_id: The child resource name.

        Returns:
            The SDK response wrapper.
        """
        return self.call_with_retry(
            self.client.get_listener,
            network_load_balancer_id=self.module.params["network_load_balancer_id"],
            listener_name=resource_id,
        )

    def mutation_kwargs(self, operation):
        """Build the SDK arguments for a child mutation.

        Args:
            operation: The lifecycle operation name.

        Returns:
            Parent ID and child identity arguments.
        """
        values = super(OciNetworkLoadBalancerListenerModule, self).mutation_kwargs(
            operation
        )
        if operation != "create":
            values["listener_name"] = self.resource_name
        return values

    create_required_fields = ("default_backend_set_name", "port", "protocol")

    update_field_specs = (
        UpdateFieldSpec(param_name="default_backend_set_name", is_mutable=True),
        UpdateFieldSpec(param_name="port", is_mutable=True),
        UpdateFieldSpec(param_name="protocol", is_mutable=True, compare="enum"),
        UpdateFieldSpec(param_name="ip_version", is_mutable=True, compare="enum"),
        UpdateFieldSpec(param_name="is_ppv2_enabled", is_mutable=True),
        UpdateFieldSpec(param_name="tcp_idle_timeout", is_mutable=True),
        UpdateFieldSpec(param_name="udp_idle_timeout", is_mutable=True),
        UpdateFieldSpec(param_name="l3_ip_idle_timeout", is_mutable=True),
    )


def main():
    """Initialize and run the listener module."""
    spec = dict(OCI_AUTH_ARGS)
    spec.update(dict(OCI_WAIT_ARGS))
    spec.update(
        dict(
            network_load_balancer_id=dict(type="str", required=True),
            name=dict(type="str", required=True),
        )
    )
    spec.update(
        dict(
            default_backend_set_name=dict(type="str"),
            port=dict(type="int"),
            protocol=dict(type="str"),
            ip_version=dict(type="str", choices=["ipv4", "ipv6"]),
            is_ppv2_enabled=dict(type="bool"),
            tcp_idle_timeout=dict(type="int"),
            udp_idle_timeout=dict(type="int"),
            l3_ip_idle_timeout=dict(type="int"),
        )
    )
    spec.update(
        dict(state=dict(type="str", choices=["present", "absent"], default="present"))
    )
    module = AnsibleModule(argument_spec=spec, supports_check_mode=True)
    OciNetworkLoadBalancerListenerModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
