# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: oci_network_loadbalancer_health_checker
short_description: Manage an OCI Network Load Balancer backend set health checker
description:
- Update the health checker for an existing backend set.
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
    description: Name of the parent backend set.
    type: str
    required: true
  protocol:
    description:
    - Health check protocol.
    - Currently supported protocols are C(http), C(https), C(tcp), C(udp), and C(dns).
    - See Oracle's documentation for the latest supported protocols at
      U(https://docs.oracle.com/en-us/iaas/Content/NetworkLoadBalancer/HealthCheckPolicies/health-check-policy-management.htm).
    type: str
  port:
    description: Port used by the health check.
    type: int
  retries:
    description: Number of retries before a backend changes health state.
    type: int
  timeout_in_millis:
    description: Maximum response time in milliseconds for each health check.
    type: int
  interval_in_millis:
    description: Time in milliseconds between health checks.
    type: int
  url_path:
    description: URL path requested by HTTP health checks.
    type: str
  response_body_regex:
    description: Regular expression used to check the response body.
    type: str
  return_code:
    description: HTTP response code for a healthy backend.
    type: int
  request_data:
    description: Base64-encoded data to send in TCP or UDP health checks.
    type: str
  response_data:
    description: Base64-encoded data expected in TCP or UDP health check responses.
    type: str
  dns:
    description: DNS health check settings.
    type: dict
    suboptions:
      transport_protocol:
        type: str
        choices:
        - udp
        - tcp
        description: Transport protocol for DNS queries.
      domain_name:
        type: str
        description: Domain name to query.
      query_class:
        type: str
        choices:
        - in
        - ch
        description: Class of DNS records to query.
      query_type:
        type: str
        choices:
        - a
        - txt
        - aaaa
        description: Type of DNS records to query.
      rcodes:
        type: list
        elements: str
        choices:
        - noerror
        - servfail
        - nxdomain
        - refused
        description: DNS response codes that indicate a healthy backend.
  wait:
    description: Whether to wait for the work request to complete.
    type: bool
    default: true
  state:
    description: Health checkers can be updated only.
    type: str
    choices:
    - present
    default: present
"""

EXAMPLES = r"""
- name: Set a TCP health check
  ansible.oci.oci_network_loadbalancer_health_checker:
    network_load_balancer_id: ocid1.networkloadbalancer.oc1..example
    name: application
    protocol: tcp
    port: 8080
    retries: 4
"""

RETURN = r"""
resource:
  description: The backend set health checker after the operation.
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
    NETWORK_LOAD_BALANCER_HEALTH_CHECKER_ARGUMENT_SPEC,
)


class OciNetworkLoadBalancerHealthCheckerModule(OciNetworkLoadBalancerSubresourceBase):
    """Update the health checker owned by a backend set."""

    update_model_name = "UpdateHealthCheckerDetails"
    update_method_name = "update_health_checker"
    update_details_name = "update_health_checker_details"
    create_resource_name = "health checker"

    def get_resource_response(self, resource_id):
        """Read the health checker for one backend set.

        Args:
            resource_id: Backend set name.

        Returns:
            The SDK response.
        """
        return self.call_with_retry(
            self.client.get_health_checker,
            network_load_balancer_id=self.module.params["network_load_balancer_id"],
            backend_set_name=resource_id,
        )

    def mutation_kwargs(self, operation):
        """Build API arguments for the parent backend set.

        Args:
            operation: The requested lifecycle operation.

        Returns:
            Parent identity arguments.
        """
        return {
            "network_load_balancer_id": self.module.params["network_load_balancer_id"],
            "backend_set_name": self.resource_name,
        }

    update_field_specs = (
        UpdateFieldSpec(param_name="protocol", is_mutable=True, compare="enum"),
        UpdateFieldSpec(param_name="port", is_mutable=True),
        UpdateFieldSpec(param_name="retries", is_mutable=True),
        UpdateFieldSpec(param_name="timeout_in_millis", is_mutable=True),
        UpdateFieldSpec(param_name="interval_in_millis", is_mutable=True),
        UpdateFieldSpec(param_name="url_path", is_mutable=True),
        UpdateFieldSpec(param_name="response_body_regex", is_mutable=True),
        UpdateFieldSpec(param_name="return_code", is_mutable=True),
        UpdateFieldSpec(param_name="request_data", is_mutable=True),
        UpdateFieldSpec(param_name="response_data", is_mutable=True),
        UpdateFieldSpec(param_name="dns", is_mutable=True, compare="nlb_dns"),
    )

    def resolve_target_resource(self):
        """Find the parent health checker or fail when its backend set is absent.

        Returns:
            The health checker model.
        """
        resource = self.get_resource_by_id(self.resource_name)
        if resource is None:
            self.module.fail_json(
                msg="Backend set {0} was not found on network load balancer {1}.".format(
                    self.resource_name, self.module.params["network_load_balancer_id"]
                )
            )
        return resource


def main():
    """Initialize and run the health checker module."""
    spec = dict(OCI_AUTH_ARGS)
    spec.update(dict(OCI_WAIT_ARGS))
    spec.update(
        dict(
            network_load_balancer_id=dict(type="str", required=True),
            name=dict(type="str", required=True),
        )
    )
    spec.update(NETWORK_LOAD_BALANCER_HEALTH_CHECKER_ARGUMENT_SPEC)
    spec.update(dict(state=dict(type="str", choices=["present"], default="present")))
    module = AnsibleModule(argument_spec=spec, supports_check_mode=True)
    OciNetworkLoadBalancerHealthCheckerModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
