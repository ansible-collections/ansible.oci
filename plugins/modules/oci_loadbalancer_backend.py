# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_loadbalancer_backend
short_description: Manage a backend server in an OCI load balancer backend set
description:
  - Create, update, or delete one backend server in an OCI load balancer backend set.
version_added: "1.2.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_wait_options
options:
  load_balancer_id:
    description:
      - The OCID of the load balancer containing the backend set.
    type: str
    required: true
  name:
    description:
      - The backend identity in C(ip_address:port) form, such as C(10.0.0.7:8080).
      - This is the backend identifier, not the compute instance display name or OCID.
      - Required for all states; on create it must match the supplied IP address and port.
      - The backend identity is creation-only and cannot change after creation.
    type: str
    required: true
  backend_set_name:
    description:
      - The name of the backend set containing the backend server.
    type: str
    required: true
  ip_address:
    description:
      - The IP address of the backend server. Required when creating a backend and must match C(name).
      - The IP address is creation-only and cannot change after creation.
      - To reproduce the Console's Compute Instances selection, supply the compute instance's private IP address.
      - Obtain the private IP address from the instance's VNIC before calling this module.
        The module accepts the IP address directly and does not resolve an instance OCID.
    type: str
  port:
    description:
      - The communication port for the backend server. Required when creating a backend and must match C(name).
      - The port is creation-only and cannot change after creation.
    type: int
  weight:
    description:
      - The backend's load balancing weight.
    type: int
  backup:
    description:
      - Whether this backend receives traffic only when other backends are unhealthy.
      - Backends marked as backup cannot be used with the IP Hash policy.
    type: bool
  drain:
    description:
      - Whether this backend should receive no new incoming traffic.
    type: bool
  offline:
    description:
      - Whether the load balancer should treat this backend as offline.
    type: bool
  wait:
    description:
      - Whether to wait for the OCI work request to complete before returning.
      - When false, the returned resource is an immediate snapshot. It may contain
        only its name if OCI has not exposed the child yet.
    type: bool
    default: true
  state:
    description:
      - The desired state of the backend server.
    type: str
    choices: [present, absent]
    default: present
"""

EXAMPLES = r"""
- name: Add a backend server
  ansible.oci.oci_loadbalancer_backend:
    load_balancer_id: ocid1.loadbalancer.oc1..example
    backend_set_name: app_pool
    name: 10.0.0.7:8080
    ip_address: 10.0.0.7
    port: 8080
    weight: 3

# Set instance_private_ip to the private IP address of the compute instance's VNIC.
- name: Register a compute instance as a backend server
  ansible.oci.oci_loadbalancer_backend:
    load_balancer_id: ocid1.loadbalancer.oc1..example
    backend_set_name: app_pool
    name: "{{ instance_private_ip }}:8080"
    ip_address: "{{ instance_private_ip }}"
    port: 8080

- name: Drain a backend server
  ansible.oci.oci_loadbalancer_backend:
    load_balancer_id: ocid1.loadbalancer.oc1..example
    backend_set_name: app_pool
    name: 10.0.0.7:8080
    drain: true

- name: Remove a backend server
  ansible.oci.oci_loadbalancer_backend:
    load_balancer_id: ocid1.loadbalancer.oc1..example
    backend_set_name: app_pool
    name: 10.0.0.7:8080
    state: absent
"""

RETURN = r"""
resource:
  description: The backend server acted upon. Not returned when C(state=absent).
  returned: when state is present
  type: dict
  contains:
    name:
      description: The backend identity in C(ip_address:port) form.
      type: str
      sample: 10.0.0.7:8080
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
    OCI_WAIT_ARGS,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_loadbalancer import (
    OciLoadBalancerSubresourceBase,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    UpdateFieldSpec,
)


class OciLoadBalancerBackendModule(OciLoadBalancerSubresourceBase):
    """Lifecycle adapter for one load balancer backend server."""

    create_model_name = "CreateBackendDetails"
    create_method_name = "create_backend_and_wait_for_state"
    create_details_name = "create_backend_details"
    update_model_name = "UpdateBackendDetails"
    update_method_name = "update_backend_and_wait_for_state"
    update_details_name = "update_backend_details"
    delete_method_name = "delete_backend_and_wait_for_state"
    create_resource_name = "load balancer backend"
    create_required_fields = ("ip_address", "port")

    update_field_specs = (
        UpdateFieldSpec(
            param_name="ip_address",
            is_mutable=False,
            immutable_reason="OCI uses the backend IP address as creation identity",
        ),
        UpdateFieldSpec(
            param_name="port",
            is_mutable=False,
            immutable_reason="OCI uses the backend port as creation identity",
        ),
        UpdateFieldSpec(param_name="weight", is_mutable=True),
        UpdateFieldSpec(param_name="backup", is_mutable=True),
        UpdateFieldSpec(param_name="drain", is_mutable=True),
        UpdateFieldSpec(param_name="offline", is_mutable=True),
    )

    def validate_create_request(self):
        """Validate required fields and the backend IP:port name."""
        super(OciLoadBalancerBackendModule, self).validate_create_request()
        expected_name = "{0}:{1}".format(
            self.module.params.get("ip_address"),
            self.module.params.get("port"),
        )
        if self.resource_name != expected_name:
            self.module.fail_json(
                msg=(
                    "The name parameter must match the supplied IP address and "
                    "port ({0}).".format(expected_name)
                )
            )

    def get_resource_response(self, resource_id):
        """Fetch the named backend.

        Args:
            resource_id: Backend name.

        Returns:
            The SDK response.
        """
        return self.call_with_retry(
            self.client.get_backend,
            load_balancer_id=self.module.params.get("load_balancer_id"),
            backend_set_name=self.module.params.get("backend_set_name"),
            backend_name=resource_id,
        )

    def mutation_kwargs(self, operation):
        """Build scoped arguments for a resource mutation.

        Args:
            operation: Create, update, or delete operation.

        Returns:
            The SDK keyword arguments.
        """
        kwargs = super(OciLoadBalancerBackendModule, self).mutation_kwargs(
            operation
        )
        kwargs["backend_set_name"] = self.module.params.get("backend_set_name")
        if operation in ("update", "delete"):
            kwargs["backend_name"] = self.resource_name
        return kwargs


def main():
    """Initialize and run the backend module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        **OCI_WAIT_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        load_balancer_id=dict(type="str", required=True),
        backend_set_name=dict(type="str", required=True),
        name=dict(type="str", required=True),
        ip_address=dict(type="str"),
        port=dict(type="int"),
        weight=dict(type="int"),
        backup=dict(type="bool"),
        drain=dict(type="bool"),
        offline=dict(type="bool"),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    OciLoadBalancerBackendModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
