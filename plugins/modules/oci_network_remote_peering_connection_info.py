# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_network_remote_peering_connection_info
short_description: Retrieve OCI remote peering connection information
description:
  - Retrieve details about one or more OCI remote peering connections.
version_added: "1.3.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  compartment_id:
    description:
      - The Oracle Cloud Identifier (OCID) of the compartment to list connections from.
      - Required when listing resources.
    type: str
  remote_peering_connection_id:
    description:
      - The OCID of a specific remote peering connection to retrieve.
      - When specified, returns a list containing that connection.
    type: str
  name:
    description:
      - Filter listed remote peering connections by name.
      - Only used when C(compartment_id) is provided.
    type: str
  drg_id:
    description:
      - Filter listed connections by the OCID of the dynamic routing gateway (DRG).
      - Only used when C(compartment_id) is provided.
    type: str
"""

EXAMPLES = r"""
- name: List all remote peering connections in a compartment
  ansible.oci.oci_network_remote_peering_connection_info:
    compartment_id: ocid1.compartment.oc1..example

- name: List remote peering connections in a compartment by name
  ansible.oci.oci_network_remote_peering_connection_info:
    compartment_id: ocid1.compartment.oc1..example
    name: example-rpc

- name: Get a specific remote peering connection
  ansible.oci.oci_network_remote_peering_connection_info:
    remote_peering_connection_id: ocid1.remotepeeringconnection.oc1..example
"""

RETURN = r"""
remote_peering_connections:
  description: List of remote peering connections that matched the query.
  returned: always
  type: list
  elements: dict
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
    - id: ocid1.remotepeeringconnection.oc1..example
      name: example-rpc
      compartment_id: ocid1.compartment.oc1..example
      drg_id: ocid1.drg.oc1..example
      lifecycle_state: AVAILABLE
      defined_tags: {"Operations": {"CostCenter": "42"}}
      time_created: "2026-01-01T00:00:00.000Z"
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import (
    OciInfoBase,
)

oci = import_oci_sdk()[0]


class OciNetworkRemotePeeringConnectionInfoModule(OciInfoBase):
    """Concrete info adapter for OCI remote peering connections."""

    @property
    def client_class(self):
        """Return the OCI virtual network client class.

        Returns:
            The SDK client class.
        """
        return oci.core.VirtualNetworkClient

    results_key = "remote_peering_connections"
    resource_id_param = "remote_peering_connection_id"
    resource_get_method = "get_remote_peering_connection"
    list_resource_method = "list_remote_peering_connections"
    list_filter_params = [
        "compartment_id",
        "drg_id",
    ]


def main():
    """Run the remote peering connection info module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        compartment_id=dict(type="str"),
        remote_peering_connection_id=dict(type="str"),
        drg_id=dict(type="str"),
        name=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["compartment_id", "remote_peering_connection_id"]],
    )

    OciNetworkRemotePeeringConnectionInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
