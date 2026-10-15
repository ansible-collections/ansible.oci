# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_identity_tag_namespace
short_description: Manage OCI tag namespaces
description:
  - Create, update, and delete OCI tag namespaces.
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
      - Set to C(present) to create or manage the namespace.
      - Set to C(absent) to retire and delete the namespace and all its tag definitions.
      - Deletion also removes these defined tags from resources across the tenancy.
      - The module waits up to C(wait_timeout) seconds and fails if deletion does not finish.
      - OCI continues deletion after the timeout.
      - Set C(wait=false) to return after OCI accepts the deletion request.
    type: str
    choices: [present, absent]
    default: present
  tag_namespace_id:
    description:
      - The OCID of the tag namespace to manage.
      - When omitted, C(compartment_id) and C(name) identify the namespace.
    type: str
  compartment_id:
    description:
      - The OCID of the compartment that contains the namespace.
      - Required when creating a namespace.
      - Scopes name lookup when C(tag_namespace_id) is omitted.
      - This value cannot change through this module after creation.
    type: str
  name:
    description:
      - The namespace name must be unique within the tenancy.
      - Required when creating a namespace.
      - OCI treats names as case-insensitive and stores the original case.
      - This value cannot change after creation.
    type: str
  description:
    description:
      - The namespace description.
      - Required when creating a namespace. An empty string is valid.
      - Can be updated.
    type: str
  is_retired:
    description:
      - Set to C(true) to retire the namespace and its tag definitions.
      - If set during creation, the module creates the namespace and then retires it.
      - Set to C(false) to activate the namespace. Retired tag definitions
        remain retired until each definition is activated separately.
      - When C(state=present), omit this option to leave the retirement state unchanged.
      - When C(state=absent), the module retires the namespace regardless of this option.
    type: bool
"""

EXAMPLES = r"""
- name: Create a tag namespace
  ansible.oci.oci_identity_tag_namespace:
    compartment_id: ocid1.tenancy.oc1..example
    name: Operations
    description: Tags for operations resources
  register: namespace

- name: Update a namespace description and tags
  ansible.oci.oci_identity_tag_namespace:
    tag_namespace_id: "{{ namespace.resource.id }}"
    description: Shared operations tags
    freeform_tags:
      owner: platform

- name: Retire a namespace
  ansible.oci.oci_identity_tag_namespace:
    tag_namespace_id: "{{ namespace.resource.id }}"
    is_retired: true

- name: Delete a namespace and its tag definitions
  ansible.oci.oci_identity_tag_namespace:
    tag_namespace_id: "{{ namespace.resource.id }}"
    state: absent
"""

RETURN = r"""
resource:
  description: The tag namespace resource.
  returned: when state=present and check mode does not predict a change
  type: dict
  contains:
    id:
      description: The OCID of the namespace.
      type: str
      returned: always
      sample: ocid1.tagnamespace.oc1..example
    compartment_id:
      description: The OCID of the namespace compartment.
      type: str
      returned: always
      sample: ocid1.tenancy.oc1..example
    name:
      description: The namespace name.
      type: str
      returned: always
      sample: Operations
    description:
      description: The namespace description.
      type: str
      returned: always
      sample: Tags for operations resources
    is_retired:
      description: Whether the namespace is retired.
      type: bool
      returned: always
      sample: false
    lifecycle_state:
      description: The current lifecycle state of the namespace.
      type: str
      returned: always
      sample: ACTIVE
    time_created:
      description: The creation time in RFC3339 format.
      type: str
      returned: always
      sample: "2026-01-01T00:00:00.000Z"
    freeform_tags:
      description: Free-form tags applied to the namespace.
      type: dict
      returned: always
      sample: {owner: platform}
    defined_tags:
      description: Defined tags applied to the namespace.
      type: dict
      returned: always
      sample: {Operations: {CostCenter: "42"}}
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    LIFECYCLE_ACTIVE,
    LIFECYCLE_DELETING,
    OCI_AUTH_ARGS,
    OCI_TAG_ARGS,
    OCI_WAIT_ARGS,
    filter_none_values,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
    UpdateFieldSpec,
)

oci = import_oci_sdk()[0]

CREATE_REQUIRED_FIELDS = ("compartment_id", "name", "description")
LIFECYCLE_INACTIVE = "INACTIVE"


def build_create_tag_namespace_details(params):
    """Build the OCI create model from module parameters.

    Args:
        params: The module parameter mapping.

    Returns:
        The OCI create details model.
    """
    details = filter_none_values(
        {
            "compartment_id": params.get("compartment_id"),
            "name": params.get("name"),
            "description": params.get("description"),
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
        }
    )
    return oci.identity.models.CreateTagNamespaceDetails(**details)


class OciIdentityTagNamespaceModule(OciResourceBase):
    """Manage tag namespaces through the OCI identity client."""

    @property
    def client_class(self):
        """Return the OCI identity client class.

        Returns:
            The OCI identity client class.
        """
        return oci.identity.IdentityClient

    resource_id_param = "tag_namespace_id"
    list_resource_method = "list_tag_namespaces"
    common_list_filter_params = ("compartment_id",)
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "tag namespace"
    name_response_field = "name"
    update_method_name = "update_tag_namespace"
    update_details_name = "update_tag_namespace_details"
    update_field_specs = (
        UpdateFieldSpec(
            param_name="compartment_id",
            is_mutable=False,
            immutable_reason="this module does not move tag namespaces between compartments",
        ),
        UpdateFieldSpec(
            param_name="name",
            is_mutable=False,
            compare="case_insensitive",
            immutable_reason="the namespace name cannot be changed",
        ),
        UpdateFieldSpec(param_name="description", is_mutable=True),
        UpdateFieldSpec(param_name="is_retired", is_mutable=True),
    )

    @property
    def update_wait_states(self):
        """Return wait states for namespace activation and retirement.

        Returns:
            The list of lifecycle states used by the update waiter.
        """
        is_retired = self.module.params.get("is_retired")
        if is_retired is True:
            return [LIFECYCLE_INACTIVE]
        if is_retired is False:
            return [LIFECYCLE_ACTIVE]
        return [LIFECYCLE_ACTIVE, LIFECYCLE_INACTIVE]

    def filter_resources_by_display_name(self, resources, name_value):
        """Match names case-insensitively because the base filter uses exact case.

        Args:
            resources: The namespace models to filter.
            name_value: The requested namespace name.

        Returns:
            Namespace models whose names match without case sensitivity.
        """
        if name_value is None:
            return resources
        requested = name_value.casefold()
        return [
            resource
            for resource in resources
            if str(getattr(resource, self.name_response_field, "")).casefold()
            == requested
        ]

    def compare_update_field_values(self, current_value, desired_value, compare=None):
        """Compare names case-insensitively because the base compares exact values.

        Args:
            current_value: The current resource field value.
            desired_value: The requested field value.
            compare: The comparison mode selected by the field specification.

        Returns:
            True when the values differ under the selected comparison.
        """
        if compare == "case_insensitive":
            return str(current_value or "").casefold() != str(desired_value or "").casefold()
        return super(OciIdentityTagNamespaceModule, self).compare_update_field_values(
            current_value, desired_value, compare
        )

    def get_resource_response(self, resource_id):
        """Fetch a namespace by OCID with the shared retry policy.

        Args:
            resource_id: The namespace OCID.

        Returns:
            The OCI response wrapper.
        """
        return self.call_with_retry(
            self.client.get_tag_namespace,
            tag_namespace_id=resource_id,
        )

    def create_resource(self):
        """Create a namespace and apply the requested retirement state.

        Returns:
            The created namespace model.
        """
        response = self.call_with_retry(
            self.client.create_tag_namespace,
            create_tag_namespace_details=build_create_tag_namespace_details(
                self.module.params
            ),
        )
        resource = self.get_mutation_result(
            response.data,
            getattr(response.data, "id", None),
            (LIFECYCLE_ACTIVE,),
        )
        if self.module.params.get("is_retired") is True:
            resource = self.update_resource(resource)
        return resource

    def build_update_details(self, update_model_fields):
        """Build the OCI namespace update model.

        Args:
            update_model_fields: Fields selected by the shared update planner.

        Returns:
            The OCI update details model.
        """
        return oci.identity.models.UpdateTagNamespaceDetails(**update_model_fields)

    def delete_resource(self, resource):
        """Retire and delete the namespace and its tag definitions.

        Args:
            resource: The namespace model to delete.

        Returns:
            The delete response or the completed work request.
        """
        if resource.lifecycle_state == LIFECYCLE_DELETING:
            return self.get_mutation_result(
                resource, resource.id, tuple(self.dead_states)
            )

        if not resource.is_retired:
            self.call_with_retry(
                self.client.update_tag_namespace,
                tag_namespace_id=resource.id,
                update_tag_namespace_details=oci.identity.models.UpdateTagNamespaceDetails(
                    is_retired=True
                ),
            )

        response = self.call_delete_fn(
            resource,
            self.client.cascade_delete_tag_namespace,
            tag_namespace_id=resource.id,
        )
        if self.module.params.get("wait", True):
            return self.wait_for_work_request(
                self.client,
                response.headers["opc-work-request-id"],
                get_work_request_fn=self.client.get_tagging_work_request,
            )
        return response


def main():
    """Create the Ansible module and run the namespace lifecycle."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        **OCI_WAIT_ARGS,
        **OCI_TAG_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        tag_namespace_id=dict(type="str"),
        compartment_id=dict(type="str"),
        name=dict(type="str"),
        description=dict(type="str"),
        is_retired=dict(type="bool"),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    OciIdentityTagNamespaceModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
