# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_instance_actions
short_description: Run an action on an OCI compute instance
description:
  - Run power, migration, or diagnostic actions on an OCI compute instance.
version_added: "1.3.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_wait_options
options:
  instance_id:
    description:
      - The OCID of the compute instance.
    type: str
    required: true
  action:
    description:
      - The action to run on the instance.
      - Each normal invocation submits the action, including C(start) and C(stop).
      - OCI can reject an action when the instance is in an invalid state.
      - C(start) powers on the instance.
      - C(stop) powers off the instance.
      - C(softstop) asks the operating system to shut down, then powers off the instance. Shutdown can take 15 minutes.
      - C(softreset) asks the operating system to shut down, then reboots the instance. Shutdown can take 15 minutes.
      - C(reset) powers off and reboots the instance.
      - C(rebootmigrate) moves the instance to new hardware, then reboots it.
      - C(senddiagnosticinterrupt) sends a diagnostic interrupt that crashes and reboots the operating system.
      - Diagnostic interrupts can cause data corruption or system failure. Configure crash dumps before use.
      - C(diagnosticreboot) rebuilds and reboots a virtual machine instance. Use it as a final troubleshooting action.
    type: str
    required: true
    choices: [start, stop, softstop, softreset, reset, rebootmigrate, senddiagnosticinterrupt, diagnosticreboot]
  delete_local_storage:
    description:
      - Whether to delete local storage during C(rebootmigrate).
      - Required as V(true) for bare metal instances with local storage. Migration deletes this storage.
      - Set this option only when you accept loss of local storage data.
    type: bool
  allow_dense_reboot_migration:
    description:
      - Whether OCI can migrate a dense I/O instance during C(reset) or C(softreset).
      - Set this option only for DenseIO instances. When true, migration permanently deletes the local SSD data.
    type: bool
notes:
  - This module is not idempotent. Each normal invocation submits a new OCI action and reports a change after success.
  - C(wait) waits for the instance lifecycle state. It does not wait for the operating system or applications.
"""

EXAMPLES = r"""
- name: Start an instance
  ansible.oci.oci_instance_actions:
    instance_id: ocid1.instance.oc1..example
    action: start

- name: Gracefully stop an instance
  ansible.oci.oci_instance_actions:
    instance_id: ocid1.instance.oc1..example
    action: softstop
    wait: true

- name: Submit a reset without waiting
  ansible.oci.oci_instance_actions:
    instance_id: ocid1.instance.oc1..example
    action: reset
    wait: false

- name: Reboot an instance and delete its local storage
  ansible.oci.oci_instance_actions:
    instance_id: ocid1.instance.oc1..example
    action: rebootmigrate
    delete_local_storage: true
"""

RETURN = r"""
action:
  description: The requested action, in lowercase.
  returned: always
  type: str
resource:
  description: The instance returned by OCI. In check mode, this contains the current instance information.
  returned: always
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_base import OciModuleBase
from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    OCI_WAIT_ARGS,
    import_oci_sdk,
)


oci = import_oci_sdk()[0]


ACTION_TO_SDK = {
    "start": "START",
    "stop": "STOP",
    "softstop": "SOFTSTOP",
    "softreset": "SOFTRESET",
    "reset": "RESET",
    "rebootmigrate": "REBOOTMIGRATE",
    "senddiagnosticinterrupt": "SENDDIAGNOSTICINTERRUPT",
    "diagnosticreboot": "DIAGNOSTICREBOOT",
}
FAILED_STATES = ["TERMINATED", "TERMINATING"]


class OciInstanceActionsModule(OciModuleBase):
    """Run an OCI instance action through the compute client."""

    @property
    def client_class(self):
        """Return the OCI ComputeClient type used by this module.

        Returns:
            The OCI ComputeClient class.
        """
        return oci.core.ComputeClient

    def process_action(self):
        """Submit the requested instance action and return the OCI response.

        Returns:
            A tuple with the change flag and the OCI response.
        Raises:
            Exception: If OCI rejects the action or the waiter fails.
        """
        params = self.module.params
        action = params["action"]
        options = {}

        if action == "rebootmigrate" and params.get("delete_local_storage") is not None:
            options["delete_local_storage"] = params["delete_local_storage"]
        elif (
            action in ("reset", "softreset")
            and params.get("allow_dense_reboot_migration") is not None
        ):
            options["allow_dense_reboot_migration"] = params["allow_dense_reboot_migration"]

        operation_kwargs = {}

        if options:
            model_name = {
                "rebootmigrate": "RebootMigrateActionDetails",
                "reset": "ResetActionDetails",
                "softreset": "SoftResetActionDetails",
            }[action]
            operation_kwargs["instance_power_action_details"] = getattr(
                oci.core.models, model_name
            )(**options)

        sdk_action = ACTION_TO_SDK[action]
        if self.module.check_mode:
            response = self.call_with_retry(
                self.client.get_instance,
                params["instance_id"],
            )
            return True, response

        wait_states = []
        waiter_kwargs = {}

        if params.get("wait"):
            wait_states = ["STOPPED"] if action in ("stop", "softstop") else ["RUNNING"]
            wait_states.extend(FAILED_STATES)
            waiter_kwargs = {
                "max_wait_seconds": params.get("wait_timeout", 1200),
                "max_interval_seconds": params.get("wait_interval", 30),
            }

        composite = oci.core.ComputeClientCompositeOperations(self.client)
        response = composite.instance_action_and_wait_for_state(
            params["instance_id"],
            sdk_action,
            wait_for_states=wait_states,
            operation_kwargs={
                "retry_strategy": oci.retry.DEFAULT_RETRY_STRATEGY,
                **operation_kwargs,
            },
            waiter_kwargs=waiter_kwargs,
        )

        if params.get("wait") and response.data.lifecycle_state in FAILED_STATES:
            raise RuntimeError(
                "Instance entered lifecycle state %s" % response.data.lifecycle_state
            )

        return True, response


def main():
    """Validate inputs, run the action, and return the module result."""
    action_choices = list(ACTION_TO_SDK)
    argument_spec = dict(
        OCI_AUTH_ARGS,
        **OCI_WAIT_ARGS,
        instance_id={"type": "str", "required": True},
        action={"type": "str", "required": True, "choices": action_choices},
        delete_local_storage={"type": "bool"},
        allow_dense_reboot_migration={"type": "bool"},
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    params = module.params
    action = params["action"]

    if params.get("delete_local_storage") is not None and action != "rebootmigrate":
        module.fail_json(
            msg="delete_local_storage is valid only with action=rebootmigrate"
        )

    if (
        params.get("allow_dense_reboot_migration") is not None
        and action not in ("reset", "softreset")
    ):
        module.fail_json(
            msg=(
                "allow_dense_reboot_migration is valid only with "
                "action=reset or action=softreset"
            )
        )

    helper = OciInstanceActionsModule(module)

    try:
        changed, response = helper.process_action()
    except Exception as exc:
        module.fail_json(
            msg="Failed to run action %s on instance %s: %s"
            % (action, params["instance_id"], str(exc))
        )

    module.exit_json(
        changed=changed,
        action=action,
        resource=helper.serialize_result_resource(response.data),
    )


if __name__ == "__main__":
    main()
