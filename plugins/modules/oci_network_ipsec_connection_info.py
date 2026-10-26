# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: oci_network_ipsec_connection_info
short_description: Retrieve OCI IPSec connections and optional tunnel data
description:
- Get one IPSec connection or list connections in a compartment.
- Set C(include_tunnels) to include existing tunnel details.
- Set C(include_shared_secret) to include tunnel secrets. This also enables tunnel details.
version_added: 1.2.0
author:
- Ron Gershburg (@ronger4)
extends_documentation_fragment:
- ansible.oci.oci_auth_options
options:
  ipsc_id:
    description: The OCID of one IPSec connection to retrieve.
    type: str
  compartment_id:
    description: The compartment OCID used for a list operation.
    type: str
  name:
    description: Filter listed connections by display name.
    type: str
  cpe_id:
    description: Filter listed connections by CPE OCID.
    type: str
  drg_id:
    description: Filter listed connections by DRG OCID.
    type: str
  include_tunnels:
    description: Include existing tunnel data in each connection result.
    type: bool
    default: false
  include_shared_secret:
    description:
    - Include each tunnel shared secret in the result.
    - This option also enables C(include_tunnels).
    - 'Protect task output with C(no_log: true) when using this option.'
    type: bool
    default: false
"""

EXAMPLES = r"""
- name: List IPSec connections with tunnels
  ansible.oci.oci_network_ipsec_connection_info:
    compartment_id: ocid1.compartment.oc1..example
    include_tunnels: true

- name: Read a connection and its shared secrets
  ansible.oci.oci_network_ipsec_connection_info:
    ipsc_id: ocid1.ipsecconnection.oc1..example
    include_shared_secret: true
  register: vpn_info
  no_log: true
"""

RETURN = r"""
ipsec_connections:
  description: Matching IPSec connections.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The OCID of the IPSec connection.
      type: str
    name:
      description: The display name of the connection.
      type: str
    compartment_id:
      description: The connection compartment OCID.
      type: str
    cpe_id:
      description: The CPE OCID.
      type: str
    drg_id:
      description: The DRG OCID.
      type: str
    cpe_local_identifier:
      description: The CPE local identifier.
      type: str
    cpe_local_identifier_type:
      description: The CPE local identifier type.
      type: str
    static_routes:
      description: Static routes for the connection.
      type: list
      elements: str
    lifecycle_state:
      description: The connection lifecycle state.
      type: str
    transport_type:
      description: The connection transport type.
      type: str
    time_created:
      description: The connection creation time.
      type: str
    freeform_tags:
      description: Free-form tags.
      type: dict
    defined_tags:
      description: Defined tags.
      type: dict
    tunnels:
      description: Tunnel details when requested.
      returned: when include_tunnels or include_shared_secret is true
      type: list
      elements: dict
      contains:
        id:
          description: The tunnel OCID.
          type: str
        name:
          description: The tunnel display name.
          type: str
        lifecycle_state:
          description: The tunnel lifecycle state.
          type: str
        status:
          description: The tunnel connectivity status.
          type: str
        vpn_ip:
          description: The Oracle VPN IP address.
          type: str
        cpe_ip:
          description: The CPE tunnel IP address.
          type: str
        routing:
          description: The tunnel routing type.
          type: str
        ike_version:
          description: The tunnel IKE version.
          type: str
        oracle_can_initiate:
          description: Whether Oracle can initiate the tunnel.
          type: str
        nat_translation_enabled:
          description: NAT traversal setting.
          type: str
        dpd_mode:
          description: Dead peer detection mode.
          type: str
        dpd_timeout_in_sec:
          description: Dead peer detection timeout.
          type: int
        shared_secret:
          description: The tunnel pre-shared key.
          returned: when include_shared_secret is true
          type: str
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import OciInfoBase

oci = import_oci_sdk()[0]


class OciNetworkIpsecConnectionInfoModule(OciInfoBase):
    """Read connections with optional tunnel and secret data."""

    @property
    def client_class(self):
        """Return the SDK client class.

        Returns:
            The OCI virtual network client class.
        """
        return oci.core.VirtualNetworkClient

    results_key = "ipsec_connections"
    resource_id_param = "ipsc_id"
    resource_get_method = "get_ip_sec_connection"
    list_resource_method = "list_ip_sec_connections"
    list_filter_params = ("compartment_id", "drg_id", "cpe_id")

    def serialize_result_resource(self, resource):
        """Extend shared serialization with requested tunnel information.

        Args:
            resource: Connection returned by the get or list operation.

        Returns:
            Connection data with optional tunnel details and secrets.
        """
        result = super().serialize_result_resource(resource)
        include_secret = self.module.params.get("include_shared_secret", False)
        if not (self.module.params.get("include_tunnels", False) or include_secret):
            return result
        tunnels = self.list_all_resources(
            self.client.list_ip_sec_connection_tunnels,
            ipsc_id=resource.id,
        )
        result["tunnels"] = []
        for tunnel in tunnels:
            value = super().serialize_result_resource(tunnel)
            if include_secret:
                secret = self.call_with_retry(
                    self.client.get_ip_sec_connection_tunnel_shared_secret,
                    ipsc_id=resource.id,
                    tunnel_id=tunnel.id,
                ).data
                value["shared_secret"] = secret.shared_secret
            result["tunnels"].append(value)
        return result


def main():
    """Initialize and run the connection info module."""
    module = AnsibleModule(
        argument_spec=dict(
            OCI_AUTH_ARGS,
            ipsc_id=dict(type="str"),
            compartment_id=dict(type="str"),
            name=dict(type="str"),
            cpe_id=dict(type="str"),
            drg_id=dict(type="str"),
            include_tunnels=dict(type="bool", default=False),
            include_shared_secret=dict(type="bool", default=False, no_log=False),
        ),
        supports_check_mode=True,
        required_one_of=[["ipsc_id", "compartment_id"]],
    )
    OciNetworkIpsecConnectionInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
