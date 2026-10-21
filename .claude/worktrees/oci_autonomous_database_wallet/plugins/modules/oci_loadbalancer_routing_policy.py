# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_loadbalancer_routing_policy
short_description: Manage a Load Balancer routing policy
description:
  - Create, update, or delete a routing policy on an OCI Load Balancer.
notes:
  - Creating a routing policy does not assign it to a listener.
  - Set C(routing_policy_name) on an HTTP or HTTPS listener to assign the policy.
  - The module sets condition language version C(V1) automatically.
version_added: "1.2.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_wait_options
options:
  load_balancer_id:
    description: OCID of the Load Balancer that contains the routing policy.
    type: str
    required: true
  name:
    description:
      - Name of the routing policy. Start the name with a letter or underscore.
      - Use only letters, digits, and underscores after the first character.
      - OCI does not allow this name to change.
    type: str
    required: true
  rules:
    description:
      - Ordered routing rules. Each rule has a name, a condition, and actions.
      - Required when creating a policy. On update, a supplied list replaces all rules in the given order.
      - If omitted during an update, the current rules stay unchanged.
    type: list
    elements: dict
    suboptions:
      name:
        description: Name of this routing rule.
        type: str
        required: true
      condition:
        description:
          - Condition expression evaluated for incoming requests.
          - See L(Routing policy language,https://docs.oracle.com/en-us/iaas/Content/Balance/Concepts/routing_policy_conditions.htm).
        type: str
        required: true
      actions:
        description:
          - Forward matching requests to the named backend set.
          - The module sets C(FORWARD_TO_BACKENDSET) automatically.
        type: list
        elements: dict
        required: true
        suboptions:
          backend_set_name:
            description: Name of the backend set that receives matching requests.
            type: str
            required: true
  wait:
    description:
      - Whether to wait for the OCI work request to complete.
      - When false, the resource is an immediate snapshot. It may contain only C(name) if OCI has not returned the policy.
    type: bool
    default: true
  state:
    description: Desired state of the routing policy.
    type: str
    choices: [present, absent]
    default: present
"""

EXAMPLES = r"""
- name: Create a routing policy
  ansible.oci.oci_loadbalancer_routing_policy:
    load_balancer_id: ocid1.loadbalancer.oc1..example
    name: image_routing
    rules:
      - name: image_requests
        condition: "http.request.url.path eq '/images'"
        actions:
          - backend_set_name: image-backends

- name: Attach a routing policy to a listener
  # The web-listener listener must exist and use HTTP or HTTPS.
  ansible.oci.oci_loadbalancer_listener:
    load_balancer_id: ocid1.loadbalancer.oc1..example
    name: web-listener
    routing_policy_name: image_routing

- name: Replace the complete ordered rule list
  ansible.oci.oci_loadbalancer_routing_policy:
    load_balancer_id: ocid1.loadbalancer.oc1..example
    name: image_routing
    rules:
      - name: image_requests
        condition: "http.request.url.path eq '/images'"
        actions:
          - backend_set_name: image-backends

- name: Delete a routing policy
  ansible.oci.oci_loadbalancer_routing_policy:
    load_balancer_id: ocid1.loadbalancer.oc1..example
    name: unused_policy
    state: absent
"""

RETURN = r"""
resource:
  description: Current routing policy, or an immediate snapshot when waiting is disabled.
  returned: when state is present, except when check mode predicts a change
  type: dict
  contains:
    name:
      description: Routing policy name.
      type: str
      returned: always
    condition_language_version:
      description: Condition language version. OCI returns C(V1).
      type: str
      returned: when available from OCI
    rules:
      description: Ordered routing rules.
      type: list
      elements: dict
      returned: when available from OCI
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    OCI_WAIT_ARGS,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_loadbalancer import (
    OciLoadBalancerSubresourceBase,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import UpdateFieldSpec


class OciLoadBalancerRoutingPolicyModule(OciLoadBalancerSubresourceBase):
    """Manage one routing policy on a Load Balancer."""

    create_model_name = "CreateRoutingPolicyDetails"
    create_method_name = "create_routing_policy_and_wait_for_state"
    create_details_name = "create_routing_policy_details"
    update_model_name = "UpdateRoutingPolicyDetails"
    update_method_name = "update_routing_policy_and_wait_for_state"
    update_details_name = "update_routing_policy_details"
    delete_method_name = "delete_routing_policy_and_wait_for_state"
    create_resource_name = "routing policy"
    create_required_fields = ("rules",)

    update_field_specs = (
        UpdateFieldSpec(param_name="rules", is_mutable=True, strategy="plan_enum_update"),
    )

    def get_resource_response(self, resource_id):
        """Fetch a routing policy by its name and parent OCID.

        The inherited getter cannot add the parent Load Balancer OCID and policy name.

        Args:
            resource_id: Routing policy name.

        Returns:
            The OCI SDK response.

        Raises:
            oci.exceptions.ServiceError: If OCI returns an error.
        """
        return self.call_with_retry(
            self.client.get_routing_policy,
            load_balancer_id=self.module.params["load_balancer_id"],
            routing_policy_name=resource_id,
        )

    def mutation_kwargs(self, operation):
        """Add the parent OCID and policy name to scoped mutation calls.

        OCI create needs the parent OCID. Update and delete also need the policy name.

        Args:
            operation: Create, update, or delete operation.

        Returns:
            SDK keyword arguments for the mutation.
        """
        kwargs = super(OciLoadBalancerRoutingPolicyModule, self).mutation_kwargs(operation)
        if operation in ("update", "delete"):
            kwargs["routing_policy_name"] = self.resource_name
        return kwargs


def main():
    """Initialize and run the routing policy module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        **OCI_WAIT_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        load_balancer_id=dict(type="str", required=True),
        name=dict(type="str", required=True),
        rules=dict(
            type="list",
            elements="dict",
            options=dict(
                name=dict(type="str", required=True),
                condition=dict(type="str", required=True),
                actions=dict(
                    type="list",
                    elements="dict",
                    required=True,
                    options=dict(backend_set_name=dict(type="str", required=True)),
                ),
            ),
        ),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    OciLoadBalancerRoutingPolicyModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
