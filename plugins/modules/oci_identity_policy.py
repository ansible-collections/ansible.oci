# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_identity_policy
short_description: Manage an OCI identity policy
description:
  - Create, update, and delete OCI identity policies.
notes:
  - Policy management requests must use the policy home region.
version_added: "1.2.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_wait_options
  - ansible.oci.oci_tags_options
options:
  state:
    description:
      - The desired lifecycle state of the policy.
    type: str
    choices: [present, absent]
    default: present
  policy_id:
    description:
      - The OCID of the policy to manage.
    type: str
  compartment_id:
    description:
      - The OCID of the compartment that contains the policy.
      - Required when creating a policy or when finding a policy by name.
      - This value cannot change after policy creation.
    type: str
  name:
    description:
      - The name of the policy.
      - Required when creating a policy.
      - This value cannot change after policy creation.
    type: str
  description:
    description:
      - The policy description. An empty value is allowed.
      - Required when creating a policy.
    type: str
  statements:
    description:
      - The full set of policy statements. This value replaces all existing statements.
      - Statement order does not affect change detection.
      - This value is required when creating a policy and cannot be empty.
    type: list
    elements: str
  version_date:
    description:
      - The policy version date in C(YYYY-MM-DD) format. This date selects service behavior for the policy.
      - On create, set an empty string to use current service behavior.
      - On an existing policy, set an empty string to clear a date and use current service behavior.
      - Omit this option to keep the current value.
    type: str
"""

EXAMPLES = r"""
- name: Create a policy
  ansible.oci.oci_identity_policy:
    compartment_id: ocid1.compartment.oc1..example
    name: example-policy
    description: Allow instance management
    statements:
      - Allow group Operators to manage instances in compartment Production

- name: Update policy statements and version date
  ansible.oci.oci_identity_policy:
    policy_id: ocid1.policy.oc1..example
    statements:
      - Allow group Operators to manage instances in compartment Production
    version_date: '2026-01-01'

- name: Delete a policy
  ansible.oci.oci_identity_policy:
    policy_id: ocid1.policy.oc1..example
    state: absent
"""

RETURN = r"""
resource:
  description: The policy resource.
  returned: when state is present and the policy is available
  type: dict
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

from datetime import date, datetime

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    OCI_TAG_ARGS,
    OCI_WAIT_ARGS,
    build_model,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
    UpdateFieldSpec,
)

oci = import_oci_sdk()[0]

CREATE_REQUIRED_FIELDS = (
    "compartment_id",
    "name",
    "description",
    "statements",
)
WAIT_FOR_POLICY_STATES = ("ACTIVE",)


def build_create_policy_details(params):
    """Build the OCI policy create model from module parameters.

    Args:
        params: The validated Ansible module parameters.

    Returns:
        The OCI CreatePolicyDetails model.
    """
    return build_model(
        {
            "compartment_id": params.get("compartment_id"),
            "name": params.get("name"),
            "description": params.get("description"),
            "statements": params.get("statements"),
            "version_date": params.get("version_date") or None,
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
        },
        oci.identity.models.CreatePolicyDetails,
    )


def validate_policy_parameters(module):
    """Validate supplied policy values before any present-state operation.

    Args:
        module: The active Ansible module instance.

    Raises:
        AnsibleModule failure when a supplied value is invalid.
    """
    if module.params.get("state", "present") != "present":
        return
    name = module.params.get("name")
    if name is not None and not name.strip():
        module.fail_json(msg="The name parameter cannot be empty or whitespace.")
    statements = module.params.get("statements")
    if statements is not None and (
        not statements
        or any(not statement or not statement.strip() for statement in statements)
    ):
        module.fail_json(
            msg="The statements parameter must contain non-empty statements."
        )
    version_date = module.params.get("version_date")
    if version_date in (None, ""):
        return
    try:
        if len(version_date) != 10 or version_date[4] != "-" or version_date[7] != "-":
            raise ValueError("Invalid date format")
        date.fromisoformat(version_date)
    except (TypeError, ValueError):
        module.fail_json(msg="version_date must use YYYY-MM-DD format or be empty.")


class OciIdentityPolicyModule(OciResourceBase):
    """Manage OCI identity policies with shared resource lifecycle helpers."""

    @property
    def client_class(self):
        """Return the OCI identity client class.

        Returns:
            The OCI IdentityClient class.
        """
        return oci.identity.IdentityClient

    resource_id_param = "policy_id"
    list_resource_method = "list_policies"
    name_response_field = "name"
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "policy"
    update_method_name = "update_policy"
    update_details_name = "update_policy_details"
    update_wait_states = WAIT_FOR_POLICY_STATES
    update_field_specs = (
        UpdateFieldSpec("name", is_mutable=False),
        UpdateFieldSpec("compartment_id", is_mutable=False),
        UpdateFieldSpec("description", is_mutable=True),
        UpdateFieldSpec(
            "statements", is_mutable=True, compare="sorted_list"
        ),
        UpdateFieldSpec(
            "version_date", is_mutable=True, compare="policy_version_date"
        ),
    )

    @staticmethod
    def policy_version_date_string(value):
        """Return a policy version date as an ISO date string.

        Args:
            value: A date value returned by OCI, or an existing string.

        Returns:
            The date as C(YYYY-MM-DD), or None when no date is set.
        """
        if isinstance(value, datetime):
            return value.date().isoformat()
        return value or None

    def compare_update_field_values(self, current_value, desired_value, compare=None):
        """Compare policy dates because OCI returns dates as SDK datetimes.

        Args:
            current_value: The value returned by OCI.
            desired_value: The value requested by the user.
            compare: The declared update comparison mode.

        Returns:
            True when the current and requested values differ.
        """
        if compare == "policy_version_date":
            current_value = self.policy_version_date_string(current_value)
            desired_value = self.policy_version_date_string(desired_value)
            return current_value != desired_value
        return super(OciIdentityPolicyModule, self).compare_update_field_values(
            current_value, desired_value, compare=compare
        )

    def build_update_plan(self, resource):
        """Keep version-date changes paired with statements in OCI requests.

        OCI applies a policy version date only when the update also includes
        statements. A statements-only update can clear an existing version date.

        Args:
            resource: The current OCI policy model.

        Returns:
            The shared update plan with required policy fields included.
        """
        update_plan = super(OciIdentityPolicyModule, self).build_update_plan(resource)
        fields = update_plan["update_model_fields"]
        current_version_date = self.policy_version_date_string(
            getattr(resource, "version_date", None)
        )
        if "version_date" in fields:
            fields.setdefault("statements", resource.statements)
        elif "statements" in fields and current_version_date:
            fields["version_date"] = current_version_date
        return update_plan

    def get_resource_response(self, resource_id):
        """Fetch a policy by OCID with the shared retry wrapper.

        Args:
            resource_id: The policy OCID.

        Returns:
            The OCI response wrapper for the policy.
        """
        return self.call_with_retry(
            self.client.get_policy, policy_id=resource_id
        )

    def create_resource(self):
        """Create a policy and wait for its active state.

        Returns:
            The created policy model after the configured wait.
        """
        details = build_create_policy_details(self.module.params)
        response = self.call_with_retry(
            self.client.create_policy, create_policy_details=details
        )
        return self.get_mutation_result(
            response.data,
            getattr(response.data, "id", None),
            WAIT_FOR_POLICY_STATES,
        )

    def build_update_details(self, update_model_fields):
        """Build the OCI policy update model from planned field changes.

        The explicit null sentinel avoids an SDK error on empty-date responses.

        Args:
            update_model_fields: The changed fields selected by the base planner.

        Returns:
            The OCI UpdatePolicyDetails model.
        """
        details = dict(update_model_fields)
        if details.get("version_date") == "":
            details["version_date"] = oci.util.NONE_SENTINEL
        return build_model(details, oci.identity.models.UpdatePolicyDetails)

    def delete_resource(self, resource):
        """Delete a policy through the shared delete and wait helper.

        Args:
            resource: The policy model to delete.

        Returns:
            The final policy model, or None when no model is returned.
        """
        return self.delete_resource_and_wait(
            resource,
            self.client.delete_policy,
            policy_id=resource.id,
        )


def main():
    """Build the Ansible argument spec and run the policy resource module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        **OCI_WAIT_ARGS,
        **OCI_TAG_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        policy_id=dict(type="str"),
        compartment_id=dict(type="str"),
        name=dict(type="str"),
        description=dict(type="str"),
        statements=dict(type="list", elements="str"),
        version_date=dict(type="str"),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    validate_policy_parameters(module)
    OciIdentityPolicyModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
