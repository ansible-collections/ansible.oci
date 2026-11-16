# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_network_remote_peering_connection
short_description: Manage an OCI remote peering connection
description:
  - Create, update, and delete OCI remote peering connections.
version_added: "1.3.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_name_lookup_options
  - ansible.oci.oci_wait_options
  - ansible.oci.oci_tags_options
options:
  state:
    description:
      - The desired lifecycle state of the remote peering connection.
    type: str
    choices: [present, absent]
    default: present
  remote_peering_connection_id:
    description:
      - The Oracle Cloud Identifier (OCID) of the remote peering connection.
      - Omit this option when creating a connection. Use the returned ID for later updates or deletion.
      - When provided, the module manages this exact remote peering connection.
      - Required to distinguish between multiple remote peering connections that share the same
        scoped C(name).
    type: str
  name:
    description:
      - The name of the remote peering connection.
      - Required when creating a remote peering connection.
      - When C(remote_peering_connection_id) is omitted, the module uses C(compartment_id + drg_id + name)
        to find an existing remote peering connection.
      - If exactly one remote peering connection matches, C(state=present) manages it as the update
        target and C(state=absent) deletes it.
      - If more than one remote peering connection matches, the task fails and the caller must
        supply C(remote_peering_connection_id).
    type: str
  compartment_id:
    description:
      - The OCID of the compartment containing the remote peering connection.
      - Required when creating a remote peering connection.
      - The module does not move an existing remote peering connection to another compartment.
      - Also scopes name-based remote peering connection lookups when C(remote_peering_connection_id) is omitted.
    type: str
  drg_id:
    description:
      - The OCID of the dynamic routing gateway (DRG) for the connection.
      - Required when creating a connection and when using name lookup.
      - This value is immutable after creation.
    type: str
"""

EXAMPLES = r"""
- name: Create a remote peering connection
  ansible.oci.oci_network_remote_peering_connection:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    drg_id: ocid1.drg.oc1..example
    name: example-rpc
  register: created_rpc

- name: Reconcile a uniquely named remote peering connection by name
  ansible.oci.oci_network_remote_peering_connection:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    drg_id: ocid1.drg.oc1..example
    name: example-rpc
    freeform_tags:
      env: prod

- name: Intentionally create a second remote peering connection with the same display name
  ansible.oci.oci_network_remote_peering_connection:
    state: present
    allow_duplicate_name: true
    compartment_id: ocid1.compartment.oc1..example
    drg_id: ocid1.drg.oc1..example
    name: example-rpc

- name: Delete the created remote peering connection
  ansible.oci.oci_network_remote_peering_connection:
    state: absent
    remote_peering_connection_id: "{{ created_rpc.resource.id }}"

- name: Delete a uniquely named remote peering connection without providing remote_peering_connection_id
  ansible.oci.oci_network_remote_peering_connection:
    state: absent
    compartment_id: ocid1.compartment.oc1..example
    drg_id: ocid1.drg.oc1..example
    name: example-rpc
"""

RETURN = r"""
resource:
  description: The remote peering connection resource.
  returned: when state != absent
  type: dict
  contains:
    id:
      description: The OCID of the remote peering connection.
      type: str
      returned: always
      sample: ocid1.remotepeeringconnection.oc1..example
    name:
      description: The display name of the remote peering connection.
      type: str
      returned: always
      sample: example-rpc
    compartment_id:
      description: The OCID of the compartment containing the remote peering connection.
      type: str
      returned: always
      sample: ocid1.compartment.oc1..example
    drg_id:
      description: The OCID of the dynamic routing gateway (DRG) for the connection.
      type: str
      returned: always
      sample: ocid1.drg.oc1..example
    lifecycle_state:
      description: The current lifecycle state of the remote peering connection.
      type: str
      returned: always
      sample: AVAILABLE
    peer_id:
      description: The OCID of the remote peer, when connected.
      type: str
    peer_region_name:
      description: The region of the remote peer, when connected.
      type: str
    peer_tenancy_id:
      description: The tenancy OCID of the remote peer, when connected.
      type: str
    peering_status:
      description: The current peering status.
      type: str
    is_cross_tenancy_peering:
      description: Whether the connection crosses tenancies.
      type: bool
    freeform_tags:
      description: Free-form tags applied to the remote peering connection.
      type: dict
      returned: always
      sample: {"environment": "production"}
    defined_tags:
      description: Defined tags applied to the remote peering connection.
      type: dict
      returned: always
      sample: {"Operations": {"CostCenter": "42"}}
    time_created:
      description: The date and time the remote peering connection was created, in RFC3339 format.
      type: str
      returned: always
      sample: "2026-01-01T00:00:00.000Z"
  sample:
    id: ocid1.remotepeeringconnection.oc1..example
    name: example-rpc
    compartment_id: ocid1.compartment.oc1..example
    drg_id: ocid1.drg.oc1..example
    lifecycle_state: AVAILABLE
    defined_tags: {"Operations": {"CostCenter": "42"}}
    time_created: "2026-01-01T00:00:00.000Z"
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    LIFECYCLE_AVAILABLE,
    OCI_COMMON_ARGS,
    filter_none_values,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
    UpdateFieldSpec,
)

oci = import_oci_sdk()[0]

CREATE_REQUIRED_FIELDS = ["compartment_id", "drg_id", "name"]
WAIT_FOR_RPC_STATES = [LIFECYCLE_AVAILABLE]


def build_create_remote_peering_connection_details(params):
    """Build the SDK create model.

    Args:
        params: Module input parameters.

    Returns:
        The SDK model for connection creation.
    """
    details = filter_none_values(
        {
            "compartment_id": params.get("compartment_id"),
            "drg_id": params.get("drg_id"),
            "display_name": params.get("name"),
            "freeform_tags": params.get("freeform_tags"),
            "defined_tags": params.get("defined_tags"),
        }
    )
    return oci.core.models.CreateRemotePeeringConnectionDetails(**details)


class OciNetworkRemotePeeringConnectionModule(OciResourceBase):
    """Concrete resource adapter for OCI remote peering connections."""

    @property
    def client_class(self):
        """Return the OCI virtual network client class.

        Returns:
            The SDK client class.
        """
        return oci.core.VirtualNetworkClient

    resource_id_param = "remote_peering_connection_id"
    list_resource_method = "list_remote_peering_connections"
    list_filter_params = ("drg_id",)
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "remote peering connection"
    update_method_name = "update_remote_peering_connection"
    update_details_name = "update_remote_peering_connection_details"
    update_wait_states = WAIT_FOR_RPC_STATES
    update_field_specs = (
        UpdateFieldSpec(
            param_name="name",
            resource_field="display_name",
            is_mutable=True,
        ),
        UpdateFieldSpec(param_name="compartment_id", is_mutable=False),
        UpdateFieldSpec(param_name="drg_id", is_mutable=False),
    )

    def get_resource_response(self, resource_id):
        """Return one remote peering connection response by OCID.

        Args:
            resource_id: The connection OCID.

        Returns:
            The OCI response containing the connection.
        """
        return self.call_with_retry(
            self.client.get_remote_peering_connection,
            remote_peering_connection_id=resource_id,
        )

    def create_resource(self):
        """Create a remote peering connection.

        Returns:
            The connection model, after optional waiting.
        """
        create_details = build_create_remote_peering_connection_details(
            self.module.params
        )
        response = self.call_with_retry(
            self.client.create_remote_peering_connection,
            create_remote_peering_connection_details=create_details,
        )
        return self.get_mutation_result(
            response.data,
            getattr(response.data, "id", None),
            WAIT_FOR_RPC_STATES,
        )

    def build_update_details(self, update_model_fields):
        """Build SDK update details from planned field changes.

        Args:
            update_model_fields: Changed fields from the shared update plan.

        Returns:
            The SDK model for connection updates.
        """
        return oci.core.models.UpdateRemotePeeringConnectionDetails(
            **update_model_fields
        )

    def delete_resource(self, resource):
        """Delete a remote peering connection.

        Args:
            resource: The connection to delete.

        Returns:
            The result after optional waiting for termination.
        """
        return self.delete_resource_and_wait(
            resource,
            self.client.delete_remote_peering_connection,
            remote_peering_connection_id=resource.id,
        )


def main():
    """Run the remote peering connection module."""
    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        remote_peering_connection_id=dict(type="str"),
        drg_id=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    OciNetworkRemotePeeringConnectionModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
