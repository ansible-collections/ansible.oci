# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_identity_tag
short_description: Manage a tag definition in an OCI tag namespace
description:
  - Creates, updates, and deletes a tag definition in an OCI tag namespace.
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
      - Desired state of the tag.
      - C(absent) retires the tag if necessary, then deletes the definition.
      - Deletion removes this tag from resources throughout the tenancy.
      - Deletion can take up to 48 hours. Set C(wait_timeout) for the required wait period.
      - If deletion is underway, C(absent) reports no change and waits when C(wait=true).
    type: str
    choices: [present, absent]
    default: present
  tag_namespace_id:
    description: OCID of the tag namespace.
    type: str
    required: true
  name:
    description:
      - Case-insensitive name of the tag.
      - Names that begin with C(oci) or C(orcl) are reserved.
      - Identifies the tag within its namespace. OCI does not permit tag renaming.
    type: str
    required: true
  description:
    description: Description of the tag. Required when the tag is created.
    type: str
  is_retired:
    description:
      - Set to C(true) to retire the tag, or C(false) to reactivate it.
      - If omitted, the retirement setting does not change.
      - For a new tag, C(true) creates the tag and then retires it.
    type: bool
  is_cost_tracking:
    description: Whether the tag is a cost-tracking tag.
    type: bool
  validator:
    description:
      - Validation rule for values assigned to the tag.
      - Omit this option to preserve the current validation rule.
      - Set C(validator_type=default) to remove the current validation rule.
    type: dict
    suboptions:
      validator_type:
        description: Type of validation rule.
        type: str
        choices: [enum, default]
        required: true
      values:
        description:
          - Allowed values for the enum validator.
          - Required when C(validator_type=enum). Supply a nonempty list of unique, nonblank strings.
          - Values are case-sensitive. C(validator_type=default) does not accept this option.
        type: list
        elements: str
"""

EXAMPLES = r"""
- name: Create a tag with an enum validator
  ansible.oci.oci_identity_tag:
    tag_namespace_id: ocid1.tagnamespace.oc1..example
    name: Environment
    description: Deployment environment
    validator:
      validator_type: enum
      values: [Development, Production]

- name: Retire and delete a tag
  ansible.oci.oci_identity_tag:
    tag_namespace_id: ocid1.tagnamespace.oc1..example
    name: Environment
    state: absent
"""

RETURN = r"""
resource:
  description: The tag definition.
  returned: when state is present and a resource is available
  type: dict
  contains:
    id:
      description: OCID of the tag definition.
      type: str
    name:
      description: Tag name with the spelling returned by OCI.
      type: str
    tag_namespace_id:
      description: OCID of the tag namespace.
      type: str
    lifecycle_state:
      description: Current tag lifecycle state.
      type: str
    is_retired:
      description: Whether the tag is retired.
      type: bool
    is_cost_tracking:
      description: Whether the tag is a cost-tracking tag.
      type: bool
    validator:
      description: Rule for values assigned to the tag.
      type: dict
    freeform_tags:
      description: Freeform tags on the definition.
      type: dict
    defined_tags:
      description: Defined tags on the definition.
      type: dict
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    OCI_TAG_ARGS,
    OCI_WAIT_ARGS,
    import_oci_sdk,
    filter_none_values,
    normalize_enum_values,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
    UpdateFieldSpec,
)

oci = import_oci_sdk()[0]


def build_tag_validator(validator):
    """Build an OCI tag validator from the module input.

    Args:
        validator: Validator options supplied by the caller.

    Returns:
        An OCI validator model, or ``None`` when validation is omitted.

    Raises:
        TypeError: When the OCI SDK rejects the validator model fields.
    """
    if validator is None:
        return None
    options = normalize_enum_values(validator, {"validator_type"})
    if options["validator_type"] == "ENUM":
        return oci.identity.models.EnumTagDefinitionValidator(**options)
    return oci.identity.models.DefaultTagDefinitionValidator(
        **filter_none_values(options)
    )


class OciIdentityTagModule(OciResourceBase):
    """Manage tag definitions scoped to one tag namespace."""

    @property
    def client_class(self):
        """Return the OCI Identity client class.

        Returns:
            The SDK class used by the inherited client constructor.
        """
        return oci.identity.IdentityClient

    resource_id_param = None
    list_resource_method = "list_tags"
    common_list_filter_params = ("tag_namespace_id",)
    name_lookup_param = "name"
    create_required_fields = ("name", "description")
    create_resource_name = "tag"
    dead_states = frozenset({"DELETED"})
    update_field_specs = (
        UpdateFieldSpec(param_name="description", is_mutable=True),
        UpdateFieldSpec(param_name="is_retired", is_mutable=True),
        UpdateFieldSpec(param_name="is_cost_tracking", is_mutable=True),
        UpdateFieldSpec(
            param_name="validator",
            is_mutable=True,
            strategy="plan_validator_update",
        ),
    )

    def validate_create_request(self):
        """Validate create fields and the requested tag validator.

        The inherited method checks required fields but does not validate enum values.

        Raises:
            SystemExit: If a required field or validator is invalid.
        """
        super(OciIdentityTagModule, self).validate_create_request()
        self.validate_validator()

    def needs_update(self, resource):
        """Validate the requested validator before update planning.

        The inherited update planner does not validate enum value constraints.

        Args:
            resource: Current OCI tag model.

        Returns:
            ``True`` when the resource needs an update.
        """
        self.validate_validator()
        return super(OciIdentityTagModule, self).needs_update(resource)

    def validate_validator(self):
        """Validate the validator dictionary and its enum values.

        Raises:
            SystemExit: If the validator options are invalid.
        """
        validator = self.module.params.get("validator")
        if validator is None:
            return
        validator_type = validator.get("validator_type")
        values = validator.get("values")
        if validator_type == "enum":
            if not isinstance(values, list) or not values:
                self.module.fail_json(msg="An enum validator requires a nonempty values list")
            if any(not isinstance(value, str) or not value.strip() for value in values):
                self.module.fail_json(msg="Enum validator values must be nonblank strings")
            if len(set(values)) != len(values):
                self.module.fail_json(msg="Enum validator values must be unique")
        elif values is not None:
            self.module.fail_json(msg="A default validator does not accept values")

    def get_resource_response(self, resource_id):
        """Get a tag by its namespace and name.

        Args:
            resource_id: Tag name used by the inherited lookup flow.

        Returns:
            The OCI response wrapper for the tag.
        """
        return self.call_with_retry(
            self.client.get_tag,
            tag_namespace_id=self.module.params["tag_namespace_id"],
            tag_name=resource_id,
        )

    def find_resources_by_name(self):
        """Resolve a name with the namespace-scoped get operation.

        The inherited list lookup returns summaries that omit validators.

        Returns:
            A list containing the matching tag, or an empty list.

        Raises:
            SystemExit: If a present request selects a tag undergoing deletion.
        """
        if not self.has_name_lookup_request:
            return []
        self.validate_name_lookup_scope()
        resource = self.get_resource_by_id(self.name_lookup_value)
        if getattr(resource, "lifecycle_state", None) == "DELETING":
            if self.module.params.get("state", "present") == "present":
                self.module.fail_json(
                    msg="The tag is DELETING. Retry the task after deletion completes."
                )
            if self.module.params.get("wait", True) and not self.check_mode:
                self.wait_for_resource_id(self.name_lookup_value, ("DELETED",))
            return []
        return [resource] if resource is not None else []

    def create_resource(self):
        """Create a tag and retire it when the request requires retirement.

        Returns:
            The created tag model after any requested retirement update.
        """
        params = self.module.params
        details = oci.identity.models.CreateTagDetails(
            name=params["name"],
            description=params["description"],
            freeform_tags=params.get("freeform_tags"),
            defined_tags=params.get("defined_tags"),
            is_cost_tracking=params.get("is_cost_tracking"),
            validator=build_tag_validator(params.get("validator")),
        )
        response = self.call_with_retry(
            self.client.create_tag,
            tag_namespace_id=params["tag_namespace_id"],
            create_tag_details=details,
        )
        resource = self.get_mutation_result(response.data, params["name"], ("ACTIVE",))
        if params.get("is_retired"):
            update = oci.identity.models.UpdateTagDetails(is_retired=True)
            response = self.call_with_retry(
                self.client.update_tag,
                tag_namespace_id=params["tag_namespace_id"],
                tag_name=params["name"],
                update_tag_details=update,
            )
            resource = self.get_mutation_result(response.data, params["name"], ("INACTIVE",))
        return resource

    def plan_validator_update(self, resource, resource_dict, spec, desired_value):
        """Plan a validator update while preserving omitted validation.

        Args:
            resource: Current OCI tag model.
            resource_dict: Serialized tag fields.
            spec: Update field specification.
            desired_value: Validator supplied by the caller.

        Returns:
            One update operation when the requested validator differs.
        """
        desired = normalize_enum_values(desired_value, {"validator_type"})
        current = resource_dict.get("validator") or {}
        current_type = current.get("validator_type")
        if current_type in (None, "DEFAULT") and desired.get("validator_type") == "DEFAULT":
            return []
        if current_type != desired.get("validator_type"):
            return [{"validator": desired}]
        if current_type == "ENUM" and self.compare_update_field_values(
            current.get("values"), desired.get("values"), compare="sorted_list"
        ):
            return [{"validator": desired}]
        return []

    def build_update_details(self, update_model_fields):
        """Build tag update details from fields with detected drift.

        Args:
            update_model_fields: Fields that need an update.

        Returns:
            OCI tag update details.
        """
        fields = dict(update_model_fields)
        if "validator" in fields:
            fields["validator"] = build_tag_validator(fields["validator"])
        return oci.identity.models.UpdateTagDetails(**fields)

    def update_resource(self, resource):
        """Update a tag with both required path arguments.

        The base update method accepts one OCID path argument. Tag updates need
        both a namespace OCID and a tag name.

        Args:
            resource: Current OCI tag model.

        Returns:
            Updated tag model.
        """
        plan = self.get_update_plan(resource)
        fields = dict(plan["update_model_fields"])
        for entry in plan["strategy_operations"]:
            for operation in entry["operations"]:
                fields.update(operation)
        if not fields:
            return resource
        details = self.build_update_details(fields)
        response = self.call_with_retry(
            self.client.update_tag,
            tag_namespace_id=self.module.params["tag_namespace_id"],
            tag_name=self.module.params["name"],
            update_tag_details=details,
        )
        desired_retired = fields.get("is_retired", getattr(resource, "is_retired", False))
        target_state = "INACTIVE" if desired_retired else "ACTIVE"
        return self.get_mutation_result(
            response.data, self.module.params["name"], (target_state,)
        )

    def delete_resource(self, resource):
        """Retire a tag before deletion and wait by tag name when requested.

        Args:
            resource: Current OCI tag model.
        """
        params = self.module.params
        tag_name = params["name"]
        if not getattr(resource, "is_retired", False):
            details = oci.identity.models.UpdateTagDetails(is_retired=True)
            response = self.call_with_retry(
                self.client.update_tag,
                tag_namespace_id=params["tag_namespace_id"],
                tag_name=tag_name,
                update_tag_details=details,
            )
            resource = self.get_mutation_result(response.data, tag_name, ("INACTIVE",))
        response = self.call_delete_fn(
            resource,
            self.client.delete_tag,
            tag_namespace_id=params["tag_namespace_id"],
            tag_name=tag_name,
        )
        self.get_mutation_result(response.data, tag_name, ("DELETED",))


def main():
    """Configure and run the tag module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        **OCI_TAG_ARGS,
        **OCI_WAIT_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        tag_namespace_id=dict(type="str", required=True),
        name=dict(type="str", required=True),
        description=dict(type="str"),
        is_retired=dict(type="bool"),
        is_cost_tracking=dict(type="bool"),
        validator=dict(
            type="dict",
            options=dict(
                validator_type=dict(type="str", choices=["enum", "default"], required=True),
                values=dict(type="list", elements="str"),
            ),
        ),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    tag_module = OciIdentityTagModule(module)
    tag_module.execute_resource_module()


if __name__ == "__main__":
    main()
