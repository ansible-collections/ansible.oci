# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_identity_policy_info
short_description: Retrieve OCI identity policy information
description:
  - Retrieve one or more OCI identity policies.
version_added: "1.2.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_info_filter_options
options:
  policy_id:
    description:
      - The OCID of the policy to retrieve.
    type: str
  compartment_id:
    description:
      - The OCID of the compartment from which to list policies.
      - Required when C(policy_id) is not set.
    type: str
  lifecycle_state:
    description:
      - Filter policies by lifecycle state.
    type: str
    choices: [creating, active, inactive, deleting, deleted]
  name:
    description:
      - Filter returned policies by exact policy name.
    type: str
"""

EXAMPLES = r"""
- name: List policies in a compartment
  ansible.oci.oci_identity_policy_info:
    compartment_id: ocid1.compartment.oc1..example
    lifecycle_state: active

- name: Find a policy by exact name
  ansible.oci.oci_identity_policy_info:
    compartment_id: ocid1.compartment.oc1..example
    name: example-policy

- name: Get a policy by OCID
  ansible.oci.oci_identity_policy_info:
    policy_id: ocid1.policy.oc1..example
"""

RETURN = r"""
policies:
  description: Policies that matched the query.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The policy OCID.
      type: str
      returned: always
    compartment_id:
      description: The OCID of the compartment that contains the policy.
      type: str
      returned: always
    name:
      description: The policy name.
      type: str
      returned: always
    statements:
      description: The policy statements.
      type: list
      elements: str
      returned: always
    description:
      description: The policy description.
      type: str
      returned: always
    time_created:
      description: The date and time when the policy was created.
      type: str
      returned: always
    lifecycle_state:
      description: The policy lifecycle state.
      type: str
      returned: always
    inactive_status:
      description: The reason that the policy is inactive.
      type: int
      returned: when available
    version_date:
      description: The policy version date.
      type: str
      returned: when available
    freeform_tags:
      description: Free-form tags applied to the policy.
      type: dict
      returned: always
    defined_tags:
      description: Defined tags applied to the policy.
      type: dict
      returned: always
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    normalize_enum_values,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import OciInfoBase

oci = import_oci_sdk()[0]


class OciIdentityPolicyInfoModule(OciInfoBase):
    """Retrieve OCI identity policies with shared get and list helpers."""

    @property
    def client_class(self):
        """Return the OCI identity client class.

        Returns:
            The OCI IdentityClient class.
        """
        return oci.identity.IdentityClient

    results_key = "policies"
    resource_id_param = "policy_id"
    resource_get_method = "get_policy"
    list_resource_method = "list_policies"
    name_response_field = "name"
    list_filter_params = ["compartment_id", "lifecycle_state"]


def main():
    """Build the Ansible argument spec and run the policy info module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        policy_id=dict(type="str"),
        compartment_id=dict(type="str"),
        lifecycle_state=dict(
            type="str",
            choices=["creating", "active", "inactive", "deleting", "deleted"],
        ),
        name=dict(type="str"),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["compartment_id", "policy_id"]],
    )
    lifecycle_state = module.params.get("lifecycle_state")
    if lifecycle_state:
        normalized = normalize_enum_values(
            {"lifecycle_state": lifecycle_state}, {"lifecycle_state"}
        )
        module.params["lifecycle_state"] = normalized["lifecycle_state"]
    OciIdentityPolicyInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
