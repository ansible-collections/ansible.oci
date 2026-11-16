# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_network_remote_peering_connection_connect
short_description: Connect remote peering connections in Oracle Cloud Infrastructure
description:
  - Connect an existing remote peering connection (RPC) to a peer on another dynamic routing gateway (DRG).
version_added: "1.3.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  remote_peering_connection_id:
    description:
      - The Oracle Cloud Identifier (OCID) of the connection that initiates peering.
      - The connection must already exist.
    type: str
    required: true
  peer_id:
    description:
      - The OCID of the peer connection.
      - The peer connection must already exist on another DRG.
      - An RPC cannot be reused for another peering relationship.
    type: str
    required: true
  peer_region_name:
    description:
      - The region that contains the peer connection, such as C(us-ashburn-1).
    type: str
    required: true
notes:
  - The requestor must have permission to connect to the peer connection.
  - This module returns after OCI accepts the request. It does not wait for peering to complete.
  - A matching pending or established connection reports no change.
  - Delete an RPC with M(ansible.oci.oci_network_remote_peering_connection) to end the peering relationship.
"""

EXAMPLES = r"""
- name: Connect two existing remote peering connections
  ansible.oci.oci_network_remote_peering_connection_connect:
    remote_peering_connection_id: ocid1.remotepeeringconnection.oc1..requestor
    peer_id: ocid1.remotepeeringconnection.oc1..acceptor
    peer_region_name: us-ashburn-1

- name: Retrieve the current peering status
  ansible.oci.oci_network_remote_peering_connection_info:
    remote_peering_connection_id: ocid1.remotepeeringconnection.oc1..requestor
"""

RETURN = r"""
resource:
  description: The current connection. Request acceptance does not confirm completed peering.
  returned: always
  type: dict
  contains:
    id:
      description: The OCID of the connection.
      type: str
    name:
      description: The connection name.
      type: str
    compartment_id:
      description: The OCID of the compartment.
      type: str
    drg_id:
      description: The OCID of the DRG.
      type: str
    peer_id:
      description: The OCID of the peer connection, when available.
      type: str
    peer_region_name:
      description: The region of the peer connection, when available.
      type: str
    peer_tenancy_id:
      description: The OCID of the peer tenancy, when available.
      type: str
    is_cross_tenancy_peering:
      description: Whether the peer belongs to another tenancy.
      type: bool
    lifecycle_state:
      description: The connection lifecycle state reported by OCI.
      type: str
    peering_status:
      description: The peering status reported by OCI.
      type: str
    defined_tags:
      description: Defined tags assigned to the connection.
      type: dict
    freeform_tags:
      description: Free-form tags assigned to the connection.
      type: dict
    time_created:
      description: The creation time in RFC3339 format.
      type: str
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_base import OciModuleBase
from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)

oci = import_oci_sdk()[0]

EXISTING_PEERING_STATUSES = frozenset({"PENDING", "PEERED"})


class OciNetworkRemotePeeringConnectionConnectModule(OciModuleBase):
    """Connect existing RPCs through the shared OCI client helpers."""

    @property
    def client_class(self):
        """Return the virtual network client class.

        Returns:
            The OCI SDK client class.
        """
        return oci.core.VirtualNetworkClient

    def get_resource_response(self):
        """Read the connection that initiates peering.

        Returns:
            The OCI response containing the connection.
        """
        try:
            return self.call_with_retry(
                self.client.get_remote_peering_connection,
                remote_peering_connection_id=self.module.params["remote_peering_connection_id"],
            )
        except Exception as exc:
            if getattr(exc, "status", None) == 404:
                self.module.fail_json(msg="The remote peering connection does not exist.")
            raise

    def connect_needed(self, resource):
        """Check whether the connection can accept a new peering request.

        Args:
            resource: The current OCI connection model.

        Returns:
            True when a connect request is required.
        """
        status = resource.peering_status
        if resource.lifecycle_state != "AVAILABLE":
            self.module.fail_json(msg="The remote peering connection must be AVAILABLE before connecting.")
        if status in EXISTING_PEERING_STATUSES:
            if (resource.peer_id == self.module.params["peer_id"]
                    and resource.peer_region_name == self.module.params["peer_region_name"]):
                return False
            self.module.fail_json(msg="The remote peering connection has a different or unresolved peer.")
        if status != "NEW":
            self.module.fail_json(msg=f"The remote peering connection cannot connect with peering_status={status}.")
        return True

    def execute_connect_module(self):
        """Submit a required connect request and return the current connection."""
        resource = self.get_resource_response().data
        changed = self.connect_needed(resource)
        if changed and not self.module.check_mode:
            details = oci.core.models.ConnectRemotePeeringConnectionsDetails(
                peer_id=self.module.params["peer_id"],
                peer_region_name=self.module.params["peer_region_name"],
            )
            self.call_with_retry(
                self.client.connect_remote_peering_connections,
                remote_peering_connection_id=self.module.params["remote_peering_connection_id"],
                connect_remote_peering_connections_details=details,
            )
            resource = self.get_resource_response().data
        self.module.exit_json(changed=changed, resource=self.serialize_result_resource(resource))


def main():
    """Run the remote peering connect module."""
    module = AnsibleModule(
        argument_spec=dict(
            OCI_AUTH_ARGS,
            remote_peering_connection_id=dict(type="str", required=True),
            peer_id=dict(type="str", required=True),
            peer_region_name=dict(type="str", required=True),
        ),
        supports_check_mode=True,
    )
    OciNetworkRemotePeeringConnectionConnectModule(module).execute_connect_module()


if __name__ == "__main__":
    main()
