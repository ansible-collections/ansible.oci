# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_loadbalancer_health_checker
short_description: Update a Load Balancer backend set health checker
description:
  - Update health-check settings for an existing backend set.
notes:
  - Omitted options use their documented defaults. This can replace existing settings.
  - Updates preserve settings without module input options,
    including C(is_force_plain_text) (Force plaintext health checks).
version_added: "1.2.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_wait_options
options:
  wait:
    description:
      - Whether to wait for the OCI work request to complete before returning.
      - When false, the module makes one immediate read after the update.
        That snapshot may show the old settings while OCI applies the change.
    type: bool
    default: true
  state:
    description:
      - Health checkers can be updated but cannot be created or deleted independently.
    type: str
    choices: [present]
    default: present
  load_balancer_id:
    description:
      - OCID of the Load Balancer containing the backend set.
    type: str
    required: true
  name:
    description:
      - Name of the backend set whose health checker is updated.
    type: str
    required: true
  protocol:
    description:
      - Protocol used for health checks, either C(http) or C(tcp).
    type: str
    choices: [http, tcp]
    default: http
  url_path:
    description:
      - Path requested by an HTTP health check.
    type: str
    default: /
  port:
    description:
      - Backend server port checked by the health checker.
    type: int
    default: 80
  return_code:
    description:
      - HTTP response code indicating a healthy backend server.
    type: int
    default: 200
  retries:
    description:
      - Number of retries before a backend server changes health state.
    type: int
    default: 3
  timeout_in_millis:
    description:
      - Maximum time in milliseconds to wait for a health-check response.
    type: int
    default: 3000
  interval_in_millis:
    description:
      - Interval between health checks, in milliseconds.
    type: int
    default: 10000
  response_body_regex:
    description:
      - Regular expression used to parse the health-check response body.
    type: str
    default: ''
"""

EXAMPLES = r"""
- name: Update a backend set health checker
  ansible.oci.oci_loadbalancer_health_checker:
    load_balancer_id: ocid1.loadbalancer.oc1..example
    name: app-backends
    url_path: /health

- name: Set a custom retry count
  ansible.oci.oci_loadbalancer_health_checker:
    load_balancer_id: ocid1.loadbalancer.oc1..example
    name: app-backends
    retries: 7

- name: Keep the custom retry count
  ansible.oci.oci_loadbalancer_health_checker:
    load_balancer_id: ocid1.loadbalancer.oc1..example
    name: app-backends
    retries: 7

- name: Reset the retry count to its default
  ansible.oci.oci_loadbalancer_health_checker:
    load_balancer_id: ocid1.loadbalancer.oc1..example
    name: app-backends
    url_path: /ready
"""

RETURN = r"""
resource:
  description: The health checker after an update.
  returned: when the existing health checker is read or an update completes
  type: dict
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
    OCI_WAIT_ARGS,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_loadbalancer import (
    OciLoadBalancerSubresourceBase,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    UpdateFieldSpec,
)


class OciLoadBalancerHealthCheckerModule(OciLoadBalancerSubresourceBase):
    """Update the health checker owned by a backend set."""

    update_model_name = "UpdateHealthCheckerDetails"
    update_method_name = "update_health_checker_and_wait_for_state"
    update_details_name = "health_checker"
    create_resource_name = "health checker"

    update_field_specs = (
        UpdateFieldSpec(param_name="protocol", is_mutable=True, strategy="plan_enum_update"),
        UpdateFieldSpec(param_name="url_path", is_mutable=True),
        UpdateFieldSpec(param_name="port", is_mutable=True),
        UpdateFieldSpec(param_name="return_code", is_mutable=True),
        UpdateFieldSpec(param_name="retries", is_mutable=True),
        UpdateFieldSpec(param_name="timeout_in_millis", is_mutable=True),
        UpdateFieldSpec(param_name="interval_in_millis", is_mutable=True),
        UpdateFieldSpec(param_name="response_body_regex", is_mutable=True),
    )

    def get_resource_response(self, resource_id):
        """Fetch the named health checker.

        Args:
            resource_id: Backend set name.

        Returns:
            The SDK response.
        """
        return self.call_with_retry(
            self.client.get_health_checker,
            load_balancer_id=self.module.params["load_balancer_id"],
            backend_set_name=resource_id,
        )

    def resolve_target_resource(self):
        """Find the health checker or fail if its backend set is missing.

        Returns:
            The current health checker SDK model.
        """
        resource = super(OciLoadBalancerHealthCheckerModule, self).resolve_target_resource()
        if resource is None:
            self.module.fail_json(
                msg=(
                    "No health checker was found for backend set "
                    "{0} on load balancer {1}. Create the backend set before "
                    "updating its health checker."
                ).format(
                    self.resource_name,
                    self.module.params.get("load_balancer_id"),
                )
            )
        return resource

    def mutation_kwargs(self, operation):
        """Build scoped arguments for a resource mutation.

        Args:
            operation: Create, update, or delete operation.

        Returns:
            The SDK keyword arguments.
        """
        kwargs = super(OciLoadBalancerHealthCheckerModule, self).mutation_kwargs(operation)
        kwargs["backend_set_name"] = self.resource_name
        return kwargs


def main():
    """Initialize and run the health checker module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        **OCI_WAIT_ARGS,
        state=dict(type="str", choices=["present"], default="present"),
        load_balancer_id=dict(type="str", required=True),
        name=dict(type="str", required=True),
        protocol=dict(type="str", choices=["http", "tcp"], default="http"),
        url_path=dict(type="str", default="/"),
        port=dict(type="int", default=80),
        return_code=dict(type="int", default=200),
        retries=dict(type="int", default=3),
        timeout_in_millis=dict(type="int", default=3000),
        interval_in_millis=dict(type="int", default=10000),
        response_body_regex=dict(type="str", default=""),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    OciLoadBalancerHealthCheckerModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
