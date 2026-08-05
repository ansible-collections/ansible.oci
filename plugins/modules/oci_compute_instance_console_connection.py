# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_compute_instance_console_connection
short_description: Manage a Compute instance console connection resource in Oracle Cloud Infrastructure
description:
  - Create and delete OCI Compute instance console connections for serial
    console access to an instance.
  - Console connections have no display name in the OCI API. Idempotency is
    based on C(instance_id) instead of a scoped name lookup: with
    C(instance_console_connection_id) omitted, C(state=present) manages the
    instance's existing non-deleted console connection (if any), and
    C(state=absent) deletes it. There is intentionally no paired
    C(oci_compute_instance_console_connection_info) module; use the
    C(resource) return value to obtain connection details.
  - Uses the shared OCI helper layer for authentication, waiting, retry
    behavior, and result shaping.
  - Create requests must omit C(instance_console_connection_id). After
    create, capture the returned connection ID and use it for later
    C(state=present) and C(state=absent) tasks.
version_added: "1.0.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - oracle.oci.oci_auth_options
  - oracle.oci.oci_wait_options
  - oracle.oci.oci_tags_options
options:
  state:
    description:
      - The desired lifecycle state of the console connection.
    type: str
    choices: [present, absent]
    default: present
  instance_console_connection_id:
    description:
      - The OCID of the console connection.
      - When provided, the module manages this exact console connection.
      - Required to distinguish between multiple console connections for the
        same C(instance_id).
    type: str
  instance_id:
    description:
      - The OCID of the instance to connect to.
      - Required when creating a console connection.
      - When C(instance_console_connection_id) is omitted, the module looks
        up the instance's existing non-deleted console connection instead.
    type: str
  compartment_id:
    description:
      - The OCID of the compartment containing the instance.
      - Required to scope the lookup used to find an existing console
        connection when C(instance_console_connection_id) is omitted.
      - Not part of the OCI create payload; the connection inherits its
        compartment from the instance.
    type: str
  public_key:
    description:
      - The SSH public key to use for the console connection.
      - Required when creating a console connection.
      - The OCI API does not return this value, so the module cannot detect
        drift on it after create.
    type: str
"""

EXAMPLES = r"""
- name: Create a console connection to an instance
  oracle.oci.oci_compute_instance_console_connection:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    instance_id: ocid1.instance.oc1..example
    public_key: "ssh-rsa AAAA..."
  register: created_console_connection

- name: Reconcile the existing console connection for an instance
  oracle.oci.oci_compute_instance_console_connection:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    instance_id: ocid1.instance.oc1..example
    public_key: "ssh-rsa AAAA..."
    freeform_tags:
      role: sre-runbook

- name: Delete the console connection by id
  oracle.oci.oci_compute_instance_console_connection:
    state: absent
    instance_console_connection_id: "{{ created_console_connection.resource.id }}"

- name: Delete an instance's console connection without tracking its id
  oracle.oci.oci_compute_instance_console_connection:
    state: absent
    compartment_id: ocid1.compartment.oc1..example
    instance_id: ocid1.instance.oc1..example
"""

RETURN = r"""
resource:
  description: The console connection resource.
  returned: when state != absent
  type: dict
  contains:
    id:
      description: The OCID of the console connection.
      type: str
      returned: always
      sample: ocid1.instanceconsoleconnection.oc1..example
    compartment_id:
      description: The OCID of the compartment containing the console connection.
      type: str
      returned: always
      sample: ocid1.compartment.oc1..example
    instance_id:
      description: The OCID of the instance the console connection belongs to.
      type: str
      returned: always
      sample: ocid1.instance.oc1..example
    lifecycle_state:
      description: The current lifecycle state of the console connection.
      type: str
      returned: always
      sample: ACTIVE
    connection_string:
      description: The SSH connection string for the console connection.
      type: str
      returned: always
      sample: ssh -o ProxyCommand='ssh -W %h:%p -p 443 ocid1.instanceconsoleconnection.oc1..example@instance-console.us-phoenix-1.oci.oraclecloud.com' -p 22 ocid1.instance.oc1..example
    vnc_connection_string:
      description: The VNC connection string for the console connection.
      type: str
      returned: always
      sample: null
    fingerprint:
      description: The SSH public key fingerprint recorded for the console connection.
      type: str
      returned: always
      sample: "12:34:56:78:9a:bc:de:f0:12:34:56:78:9a:bc:de:f0"
    freeform_tags:
      description: Free-form tags applied to the console connection.
      type: dict
      returned: always
      sample: {"environment": "production"}
    defined_tags:
      description: Defined tags applied to the console connection.
      type: dict
      returned: always
      sample: {"Operations": {"CostCenter": "42"}}
  sample:
    id: ocid1.instanceconsoleconnection.oc1..example
    compartment_id: ocid1.compartment.oc1..example
    instance_id: ocid1.instance.oc1..example
    lifecycle_state: ACTIVE
    connection_string: ssh -o ProxyCommand='ssh -W %h:%p -p 443 ocid1.instanceconsoleconnection.oc1..example@instance-console.us-phoenix-1.oci.oraclecloud.com' -p 22 ocid1.instance.oc1..example
    vnc_connection_string: null
    fingerprint: "12:34:56:78:9a:bc:de:f0:12:34:56:78:9a:bc:de:f0"
    freeform_tags: {"environment": "production"}
    defined_tags: {"Operations": {"CostCenter": "42"}}
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.oracle.oci.plugins.module_utils.oci_common import (
    LIFECYCLE_ACTIVE,
    OCI_AUTH_ARGS,
    OCI_TAG_ARGS,
    OCI_WAIT_ARGS,
    DEAD_STATES,
    filter_none_values,
    import_oci_sdk,
)
from ansible_collections.oracle.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
)

imported_oci_sdk = import_oci_sdk()
oci = imported_oci_sdk[0]
HAS_OCI_SDK = imported_oci_sdk[1]

CREATE_REQUIRED_FIELDS = [
    "compartment_id",
    "instance_id",
    "public_key",
]
WAIT_FOR_CONSOLE_CONNECTION_STATES = [LIFECYCLE_ACTIVE]


def build_create_console_connection_details(params):
    details = filter_none_values(
        {
            "instance_id": params.get("instance_id"),
            "public_key": params.get("public_key"),
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
        }
    )
    return oci.core.models.CreateInstanceConsoleConnectionDetails(**details)


class OciComputeInstanceConsoleConnectionModule(OciResourceBase):
    """Concrete resource adapter for OCI Compute instance console connections.

    Console connections have no display name in the OCI API, so this module
    does not use the shared scoped name-lookup mechanism. Instead it looks up
    the instance's existing non-deleted console connection directly.
    """

    @property
    def client_class(self):
        return oci.core.ComputeClient

    resource_id_param = "instance_console_connection_id"
    name_lookup_param = None
    list_resource_method = "list_instance_console_connections"
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "console connection"
    update_method_name = "update_instance_console_connection"
    update_details_name = "update_instance_console_connection_details"
    update_wait_states = WAIT_FOR_CONSOLE_CONNECTION_STATES
    update_field_specs = [
        {
            "param_name": "instance_id",
            "resource_field": "instance_id",
            "is_mutable": False,
        },
    ]

    def resolve_target_resource(self):
        if self.resource_id:
            return self.get_resource_by_id(self.resource_id)
        return self._find_active_connection_for_instance()

    def _find_active_connection_for_instance(self):
        instance_id = self.module.params.get("instance_id")
        compartment_id = self.module.params.get("compartment_id")
        if not instance_id or not compartment_id:
            return None

        connections = self.list_all_resources(
            self.client.list_instance_console_connections,
            compartment_id=compartment_id,
            instance_id=instance_id,
        )
        active_connections = [
            connection
            for connection in connections
            if getattr(connection, "lifecycle_state", None) not in DEAD_STATES
        ]
        if not active_connections:
            return None
        if len(active_connections) > 1:
            self.module.fail_json(
                msg=(
                    f"Multiple active console connections were found for "
                    f"instance_id={instance_id}. Provide "
                    f"instance_console_connection_id to distinguish between "
                    f"{len(active_connections)} matches."
                )
            )
        return active_connections[0]

    def validate_delete_request(self):
        if self.resource_id:
            return
        if not self.module.params.get("instance_id") or not self.module.params.get(
            "compartment_id"
        ):
            self.module.fail_json(
                msg=(
                    "Deleting a console connection requires either "
                    "instance_console_connection_id, or both instance_id "
                    "and compartment_id"
                )
            )

    def get_resource_response(self, resource_id):
        return self.call_with_retry(
            self.client.get_instance_console_connection,
            instance_console_connection_id=resource_id,
        )

    def create_resource(self):
        response = self.call_with_retry(
            self.client.create_instance_console_connection,
            create_instance_console_connection_details=build_create_console_connection_details(
                self.module.params
            ),
        )
        return self.get_mutation_result(
            response.data,
            getattr(response.data, "id", None),
            WAIT_FOR_CONSOLE_CONNECTION_STATES,
        )

    def build_update_details(self, update_model_fields):
        return oci.core.models.UpdateInstanceConsoleConnectionDetails(
            **update_model_fields
        )

    def delete_resource(self, resource):
        return self.delete_resource_and_wait(
            resource,
            self.client.delete_instance_console_connection,
            instance_console_connection_id=resource.id,
        )


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        **OCI_WAIT_ARGS,
        **OCI_TAG_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        instance_console_connection_id=dict(type="str"),
        instance_id=dict(type="str"),
        compartment_id=dict(type="str"),
        public_key=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    OciComputeInstanceConsoleConnectionModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
