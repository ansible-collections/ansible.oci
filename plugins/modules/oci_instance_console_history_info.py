# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_instance_console_history_info
short_description: Retrieve OCI Compute instance console history metadata
description:
  - Retrieve console history metadata and optionally return content as base64.
version_added: "1.3.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  compartment_id:
    description:
      - The OCID of the compartment to list.
      - Required when you omit O(instance_console_history_id).
    type: str
  instance_console_history_id:
    description:
      - The OCID of one capture to retrieve.
    type: str
  name:
    description:
      - Filter list results by exact display name.
    type: str
  instance_id:
    description:
      - Filter list results by instance OCID.
    type: str
  lifecycle_state:
    description:
      - Filter listed captures by lifecycle state.
      - This option applies only when listing captures by compartment.
    type: str
    choices: [requested, getting_history, succeeded, failed]
  include_content:
    description:
      - Return the raw console bytes as Base64 for a successful capture.
      - Requires O(instance_console_history_id).
      - Set C(no_log) on the task if the console data contains sensitive information.
    type: bool
    default: false
"""

EXAMPLES = r"""
- name: List successful captures for an instance
  ansible.oci.oci_instance_console_history_info:
    compartment_id: ocid1.compartment.oc1..example
    instance_id: ocid1.instance.oc1..example
    lifecycle_state: succeeded

- name: Read the console data for a capture
  ansible.oci.oci_instance_console_history_info:
    instance_console_history_id: ocid1.instanceconsolehistory.oc1..example
    include_content: true
  register: console_history
  no_log: true

- name: Save the console data to a file
  ansible.builtin.shell:
    cmd: umask 077 && base64 --decode > console-history.log
    stdin: "{{ console_history.instance_console_histories[0].content_base64 }}"
  when: console_history.instance_console_histories | length > 0
  no_log: true
"""

RETURN = r"""
instance_console_histories:
  description: Matching console history metadata.
  returned: always
  type: list
  elements: dict
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
    content_base64:
      description: The captured bytes in Base64.
      returned: when include_content is true and the capture exists
      type: str
"""

import base64

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
    normalize_choice_parameters,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import OciInfoBase

oci = import_oci_sdk()[0]
STATE_MAP = {
    "requested": "REQUESTED",
    "getting_history": "GETTING-HISTORY",
    "succeeded": "SUCCEEDED",
    "failed": "FAILED",
}


class OciInstanceConsoleHistoryInfoModule(OciInfoBase):
    """Retrieve OCI Compute instance console history metadata and content."""

    @property
    def client_class(self):
        """Get the client class for the Compute service.

        Returns:
            The OCI Compute client class.
        """
        return oci.core.ComputeClient

    results_key = "instance_console_histories"
    resource_id_param = "instance_console_history_id"
    resource_get_method = "get_console_history"
    list_resource_method = "list_console_histories"
    list_filter_params = ("compartment_id", "instance_id", "lifecycle_state")

    def serialize_result_resource(self, resource):
        """Add capture content because the SDK returns it from a separate operation.

        Args:
            resource: The OCI model with capture metadata.

        Returns:
            The capture metadata and the encoded bytes, if requested.
        """
        result = super().serialize_result_resource(resource)
        if self.module.params.get("include_content"):
            state = getattr(resource, "lifecycle_state", None)
            if state != "SUCCEEDED":
                self.module.fail_json(
                    msg=f"Capture {resource.id} is in state {state}. "
                    "The capture must be in state SUCCEEDED to get its content."
                )
            content = self.call_with_retry(
                self.client.get_console_history_content,
                instance_console_history_id=resource.id,
            ).data
            result["content_base64"] = base64.b64encode(content).decode("ascii")
        return result


def main():
    """Run the instance console history info module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        instance_console_history_id=dict(type="str"),
        name=dict(type="str"),
        lifecycle_state=dict(type="str", choices=list(STATE_MAP)),
        include_content=dict(type="bool", default=False),
        compartment_id=dict(type="str"),
        instance_id=dict(type="str"),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["compartment_id", "instance_console_history_id"]],
        required_if=[["include_content", True, ["instance_console_history_id"]]],
    )
    normalize_choice_parameters(module, {("lifecycle_state",): STATE_MAP})
    OciInstanceConsoleHistoryInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
