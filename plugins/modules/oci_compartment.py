# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_compartment
short_description: Manage OCI compartments
description:
  - Create, update, and delete OCI compartments.
  - Create a nested compartment by setting C(parent_compartment_id) to the
    OCID of an existing compartment. A tenancy OCID can be used to create a
    top-level compartment.
  - When C(compartment_id) is omitted, C(parent_compartment_id + name) finds
    the existing compartment for idempotent create and delete operations.
version_added: "1.1.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_wait_options
  - ansible.oci.oci_tags_options
options:
  state:
    description:
      - The desired lifecycle state of the compartment.
    type: str
    choices: [present, absent]
    default: present
  compartment_id:
    description:
      - The OCID of the compartment to manage.
      - When supplied, the module manages this exact compartment.
    type: str
  parent_compartment_id:
    description:
      - The OCID of the parent compartment.
      - Required when creating a compartment. Use the tenancy OCID to create a
        top-level compartment, or a compartment OCID to create a nested one.
      - Also scopes name-based lookup when C(compartment_id) is omitted.
      - When used with C(compartment_id), resolves that compartment from the
        parent's direct children instead of calling C(GetCompartment).
      - The module does not move an existing compartment to another parent.
    type: str
  name:
    description:
      - The name of the compartment.
      - Required when creating a compartment.
      - Can be updated in place.
    type: str
  description:
    description:
      - The description of the compartment.
      - Required when creating a compartment, but may be an empty string.
      - Can be updated in place.
    type: str
"""

EXAMPLES = r"""
- name: Create a nested compartment
  ansible.oci.oci_compartment:
    state: present
    parent_compartment_id: ocid1.compartment.oc1..example
    name: project-development
    description: Development resources for the project
  register: project_compartment

- name: Reconcile the compartment by parent and name
  ansible.oci.oci_compartment:
    state: present
    parent_compartment_id: ocid1.compartment.oc1..example
    name: project-development
    description: Updated development resources for the project
    freeform_tags:
      environment: development

- name: Delete the compartment
  ansible.oci.oci_compartment:
    state: absent
    compartment_id: "{{ project_compartment.resource.id }}"
"""

RETURN = r"""
resource:
  description: The compartment resource.
  returned: when state != absent
  type: dict
  contains:
    id:
      description: The OCID of the compartment.
      type: str
      returned: always
      sample: ocid1.compartment.oc1..example
    compartment_id:
      description: The OCID of the parent compartment.
      type: str
      returned: always
      sample: ocid1.compartment.oc1..parent-example
    name:
      description: The name of the compartment.
      type: str
      returned: always
      sample: project-development
    description:
      description: The compartment description.
      type: str
      returned: always
      sample: Development resources for the project
    lifecycle_state:
      description: The current lifecycle state of the compartment.
      type: str
      returned: always
      sample: ACTIVE
    time_created:
      description: The creation time in RFC3339 format.
      type: str
      returned: always
      sample: "2026-01-01T00:00:00.000Z"
    freeform_tags:
      description: Free-form tags applied to the compartment.
      type: dict
      returned: always
      sample: {"environment": "development"}
    defined_tags:
      description: Defined tags applied to the compartment.
      type: dict
      returned: always
      sample: {"Operations": {"CostCenter": "42"}}
"""

from types import SimpleNamespace

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    LIFECYCLE_ACTIVE,
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

imported_oci_sdk = import_oci_sdk()
oci = imported_oci_sdk[0]
HAS_OCI_SDK = imported_oci_sdk[1]

CREATE_REQUIRED_FIELDS = (
    "parent_compartment_id",
    "name",
    "description",
)
WAIT_FOR_COMPARTMENT_STATES = (LIFECYCLE_ACTIVE,)


def build_create_compartment_details(params):
    details = filter_none_values(
        {
            "compartment_id": params.get("parent_compartment_id"),
            "name": params.get("name"),
            "description": params.get("description"),
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
        }
    )
    return oci.identity.models.CreateCompartmentDetails(**details)


class OciCompartmentModule(OciResourceBase):
    """Concrete resource adapter for OCI compartments."""

    @property
    def client_class(self):
        return oci.identity.IdentityClient

    resource_id_param = "compartment_id"
    list_resource_method = "list_compartments"
    common_list_filter_params = ("parent_compartment_id",)
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "compartment"
    update_method_name = "update_compartment"
    update_details_name = "update_compartment_details"
    update_wait_states = WAIT_FOR_COMPARTMENT_STATES
    update_field_specs = (
        UpdateFieldSpec(param_name="name", is_mutable=True),
        UpdateFieldSpec(param_name="description", is_mutable=True),
    )

    def find_resources_by_name(self):
        if not self.has_name_lookup_request:
            return []
        self.validate_name_lookup_scope()
        return self.list_all_resources(
            self.client.list_compartments,
            compartment_id=self.module.params["parent_compartment_id"],
            name=self.name_lookup_value,
            lifecycle_state=LIFECYCLE_ACTIVE,
        )

    def get_resource_response(self, resource_id):
        return self.call_with_retry(
            self.client.get_compartment,
            compartment_id=resource_id,
        )

    def get_resource_by_id(self, resource_id):
        parent_compartment_id = self.module.params.get("parent_compartment_id")
        if not parent_compartment_id:
            return super(OciCompartmentModule, self).get_resource_by_id(resource_id)

        resources = self.list_all_resources(
            self.client.list_compartments,
            compartment_id=parent_compartment_id,
        )
        return next(
            (
                resource
                for resource in resources
                if getattr(resource, "id", None) == resource_id
            ),
            None,
        )

    def wait_for_resource_id(self, resource_id, target_states, failure_states=None):
        if not self.module.params.get("parent_compartment_id"):
            return super(OciCompartmentModule, self).wait_for_resource_id(
                resource_id,
                target_states,
                failure_states,
            )

        if not self.module.params.get("wait", True):
            return self.get_resource_by_id(resource_id)

        if failure_states is None:
            failure_states = frozenset({"FAILED"})

        target_is_deleted = any(state in self.dead_states for state in target_states)

        def fetch_response(response=None):
            return SimpleNamespace(data=self.get_resource_by_id(resource_id))

        def wait_complete(response):
            resource = response.data
            if resource is None:
                return target_is_deleted

            state = getattr(resource, "lifecycle_state", None)
            if state in failure_states:
                self.module.fail_json(
                    msg=f"Resource {resource_id} entered failure state: {state}",
                )
            return state in target_states

        waiter_result = oci.wait_until(
            self.client,
            fetch_response(),
            max_interval_seconds=self.module.params.get("wait_interval", 30),
            max_wait_seconds=self.module.params.get("wait_timeout", 1200),
            evaluate_response=wait_complete,
            fetch_func=fetch_response,
        )
        return getattr(waiter_result, "data", None)

    def create_resource(self):
        response = self.call_with_retry(
            self.client.create_compartment,
            create_compartment_details=build_create_compartment_details(
                self.module.params
            ),
        )
        return self.get_mutation_result(
            response.data,
            getattr(response.data, "id", None),
            WAIT_FOR_COMPARTMENT_STATES,
        )

    def build_update_details(self, update_model_fields):
        return oci.identity.models.UpdateCompartmentDetails(**update_model_fields)

    def delete_resource(self, resource):
        return self.delete_resource_and_wait(
            resource,
            self.client.delete_compartment,
            compartment_id=resource.id,
        )


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        **OCI_WAIT_ARGS,
        **OCI_TAG_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        compartment_id=dict(type="str"),
        parent_compartment_id=dict(type="str"),
        name=dict(type="str"),
        description=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    OciCompartmentModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
