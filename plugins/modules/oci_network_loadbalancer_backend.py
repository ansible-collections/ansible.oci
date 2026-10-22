# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: oci_network_loadbalancer_backend
short_description: Manage an OCI Network Load Balancer backend
description:
- Create, update, or delete an OCI Network Load Balancer backend.
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
    description: The backend name.
    type: str
    required: true
  backend_set_name:
    description: The parent backend set name.
    type: str
    required: true
  ip_address:
    description:
    - IP address of the backend. Supply this or target_id when you create the backend.
    - Supply one address that matches the IP version of the parent backend set.
    - This value cannot change after creation.
    type: str
  target_id:
    description: OCID of the backend target. Supply this or ip_address when you create the backend. This
      value cannot change after creation.
    type: str
  port:
    description: Backend port. Required when you create the backend. This value cannot change after creation.
    type: int
  weight:
    description: Weight used to distribute traffic to this backend.
    type: int
  is_backup:
    description: Whether to use this backend only when primary backends are unavailable.
    type: bool
  is_drain:
    description: Whether to stop new connections while preserving existing connections.
    type: bool
  is_offline:
    description: Whether to stop sending traffic to this backend.
    type: bool
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
- name: Add a backend by IP address
  ansible.oci.oci_network_loadbalancer_backend:
    network_load_balancer_id: ocid1.networkloadbalancer.oc1..example
    backend_set_name: application
    name: app-a
    ip_address: 10.0.0.10
    port: 8080
    weight: 2

- name: Drain a backend
  ansible.oci.oci_network_loadbalancer_backend:
    network_load_balancer_id: ocid1.networkloadbalancer.oc1..example
    backend_set_name: application
    name: app-a
    is_drain: true
"""

RETURN = r"""
resource:
  description: The backend after the operation.
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
    NETWORK_LOAD_BALANCER_BACKEND_ARGUMENT_SPEC,
    validate_network_load_balancer_backend,
)


class OciNetworkLoadBalancerBackendModule(OciNetworkLoadBalancerSubresourceBase):
    """Manage one backend."""

    create_model_name = "CreateBackendDetails"
    create_method_name = "create_backend"
    create_details_name = "create_backend_details"
    update_model_name = "UpdateBackendDetails"
    update_method_name = "update_backend"
    update_details_name = "update_backend_details"
    delete_method_name = "delete_backend"
    create_resource_name = "backend"

    def get_resource_response(self, resource_id):
        """Read one child resource from OCI.

        Args:
            resource_id: The child resource name.

        Returns:
            The SDK response wrapper.
        """
        return self.call_with_retry(
            self.client.get_backend,
            network_load_balancer_id=self.module.params["network_load_balancer_id"],
            backend_name=resource_id,
            backend_set_name=self.module.params["backend_set_name"],
        )

    def mutation_kwargs(self, operation):
        """Build the SDK arguments for a child mutation.

        Args:
            operation: The lifecycle operation name.

        Returns:
            Parent ID and child identity arguments.
        """
        values = super(OciNetworkLoadBalancerBackendModule, self).mutation_kwargs(
            operation
        )
        values["backend_set_name"] = self.module.params["backend_set_name"]
        if operation != "create":
            values["backend_name"] = self.resource_name
        return values

    update_field_specs = (
        UpdateFieldSpec(
            param_name="ip_address",
            is_mutable=False,
            immutable_reason="Backend address is creation-only",
        ),
        UpdateFieldSpec(
            param_name="target_id",
            is_mutable=False,
            immutable_reason="Backend target is creation-only",
        ),
        UpdateFieldSpec(
            param_name="port",
            is_mutable=False,
            immutable_reason="Backend port is creation-only",
        ),
        UpdateFieldSpec(param_name="weight", is_mutable=True),
        UpdateFieldSpec(param_name="is_backup", is_mutable=True),
        UpdateFieldSpec(param_name="is_drain", is_mutable=True),
        UpdateFieldSpec(param_name="is_offline", is_mutable=True),
    )

    def validate_create_request(self):
        """Check the backend locator requirement that field lists cannot express."""
        validate_network_load_balancer_backend(self.module, self.module.params)


def main():
    """Initialize and run the backend module."""
    spec = dict(OCI_AUTH_ARGS)
    spec.update(OCI_WAIT_ARGS)
    spec.update(NETWORK_LOAD_BALANCER_BACKEND_ARGUMENT_SPEC)
    spec.update(
        dict(
            network_load_balancer_id=dict(type="str", required=True),
            name=dict(type="str", required=True),
        )
    )
    spec.update(dict(backend_set_name=dict(type="str", required=True)))
    spec.update(
        dict(state=dict(type="str", choices=["present", "absent"], default="present"))
    )
    module = AnsibleModule(argument_spec=spec, supports_check_mode=True)
    OciNetworkLoadBalancerBackendModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
