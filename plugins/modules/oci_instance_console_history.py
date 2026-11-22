# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_instance_console_history
short_description: Manage an OCI Compute instance console history capture
description:
  - Create or delete a serial console capture for a Compute instance.
  - Update the name and tags of an existing capture.
version_added: "1.3.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_wait_options
  - ansible.oci.oci_tags_options
  - ansible.oci.oci_name_lookup_options
options:
  state:
    description:
      - Use C(present) to create a capture or update its metadata.
      - In normal mode, C(present) with O(wait=true) waits for an existing capture to succeed.
      - Use C(absent) to delete a capture.
    type: str
    choices: [present, absent]
    default: present
  instance_console_history_id:
    description:
      - The OCID of the capture.
      - If you supply this option, the module selects the capture by OCID.
    type: str
  name:
    description:
      - The display name of the capture.
      - Supply this option for lookup when you omit O(instance_console_history_id).
      - Use a new name to make a fresh capture.
    type: str
  instance_id:
    description:
      - The OCID of the instance.
      - Supply this option when you omit O(instance_console_history_id).
      - Before you create a capture, create a console connection for the instance.
    type: str
  compartment_id:
    description:
      - The OCID of the instance compartment.
      - Supply this option when you omit O(instance_console_history_id).
    type: str
"""

EXAMPLES = r"""
- name: Capture the instance console history
  ansible.oci.oci_instance_console_history:
    compartment_id: ocid1.compartment.oc1..example
    instance_id: ocid1.instance.oc1..example
    name: boot-console
  register: console_history

- name: Update the capture name by OCID
  ansible.oci.oci_instance_console_history:
    instance_console_history_id: "{{ console_history.resource.id }}"
    name: first-boot-console

- name: Delete the capture by OCID
  ansible.oci.oci_instance_console_history:
    instance_console_history_id: "{{ console_history.resource.id }}"
    state: absent
"""

RETURN = r"""
resource:
  description: Console history metadata.
  returned: when state is present and capture metadata is available
  type: dict
  contains:
    id:
      description: The OCID of the capture.
      type: str
    name:
      description: The display name of the capture.
      type: str
    instance_id:
      description: The OCID of the instance.
      type: str
    compartment_id:
      description: The OCID of the instance compartment.
      type: str
    lifecycle_state:
      description: The current lifecycle state of the capture.
      type: str
      sample: SUCCEEDED
    availability_domain:
      description: The availability domain of the instance.
      type: str
    defined_tags:
      description: The defined tags of the capture.
      type: dict
    freeform_tags:
      description: The free-form tags of the capture.
      type: dict
    time_created:
      description: The time when OCI created the capture.
      type: str
"""

import uuid

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    DEAD_STATES,
    OCI_COMMON_ARGS,
    filter_none_values,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
    UpdateFieldSpec,
)

oci = import_oci_sdk()[0]
WAIT_STATES = ("SUCCEEDED",)


def build_capture_details(params):
    """Build capture details from module parameters.

    Args:
        params: Module parameters.

    Returns:
        An OCI capture-details model.
    """
    return oci.core.models.CaptureConsoleHistoryDetails(
        **filter_none_values(
            {
                "instance_id": params.get("instance_id"),
                "display_name": params.get("name"),
                "freeform_tags": params.get("freeform_tags"),
                "defined_tags": params.get("defined_tags"),
            }
        )
    )


class OciInstanceConsoleHistoryModule(OciResourceBase):
    """Manage OCI Compute instance console history captures."""

    @property
    def client_class(self):
        """Get the client class for the Compute service.

        Returns:
            The OCI Compute client class.
        """
        return oci.core.ComputeClient

    resource_id_param = "instance_console_history_id"
    list_resource_method = "list_console_histories"
    list_filter_params = ("instance_id",)
    create_required_fields = ("instance_id", "compartment_id", "name")
    create_resource_name = "instance console history"
    update_method_name = "update_console_history"
    update_details_name = "update_console_history_details"
    update_wait_states = None
    update_field_specs = (
        UpdateFieldSpec(
            param_name="name",
            resource_field="display_name",
            update_field="display_name",
            is_mutable=True,
        ),
        UpdateFieldSpec(param_name="instance_id", is_mutable=False),
        UpdateFieldSpec(param_name="compartment_id", is_mutable=False),
    )

    def resolve_target_resource(self):
        """Resolve the selected capture and wait when it has not succeeded.

        The base lookup returns the current state. Captures can still be
        pending when a later run selects them.

        Returns:
            The capture metadata, or None if the lookup finds no capture.
        """
        resource = super().resolve_target_resource()
        if (
            resource is not None
            and self.module.params.get("state", "present") == "present"
            and self.module.params.get("wait", True)
            and not self.check_mode
            and resource.lifecycle_state not in WAIT_STATES
        ):
            return self.wait_for_resource_id(resource.id, WAIT_STATES)
        return resource

    def validate_create_request(self):
        """Verify the instance compartment because OCI derives it during capture."""
        super().validate_create_request()
        response = self.call_with_retry(
            self.client.get_instance,
            instance_id=self.module.params["instance_id"],
        )
        if response.data.compartment_id != self.module.params["compartment_id"]:
            self.module.fail_json(msg="The instance does not belong to the specified compartment.")

    def get_resource_response(self, resource_id):
        """Get console history metadata by OCID.

        Args:
            resource_id: The OCID of the capture.

        Returns:
            The OCI response with capture metadata.
        """
        return self.call_with_retry(
            self.client.get_console_history,
            instance_console_history_id=resource_id,
        )

    def create_resource(self):
        """Capture console history and wait for completion when requested.

        Returns:
            The OCI model with capture metadata.
        """
        response = self.call_with_retry(
            self.client.capture_console_history,
            capture_console_history_details=build_capture_details(self.module.params),
            opc_retry_token=str(uuid.uuid4()),
        )
        return self.get_mutation_result(response.data, response.data.id, WAIT_STATES)

    def build_update_details(self, update_model_fields):
        """Build update details for mutable metadata fields.

        Args:
            update_model_fields: Changed fields in the OCI update model.

        Returns:
            The OCI update model.
        """
        return oci.core.models.UpdateConsoleHistoryDetails(**update_model_fields)

    def delete_resource(self, resource):
        """Delete a capture and wait for the service to remove it.

        Args:
            resource: The OCI model for the capture to delete.

        Raises:
            ServiceError: If the OCI delete operation fails and the capture still exists.
        """
        try:
            self.call_delete_fn(
                resource,
                self.client.delete_console_history,
                instance_console_history_id=resource.id,
            )
        except oci.exceptions.ServiceError as exc:
            if exc.status == 404:
                return
            raise
        if not self.module.params.get("wait", True):
            return
        self.wait_for_resource_id(resource.id, DEAD_STATES, failure_states=())


def main():
    """Run the instance console history resource module."""
    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        instance_console_history_id=dict(type="str"),
        instance_id=dict(type="str"),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    OciInstanceConsoleHistoryModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
