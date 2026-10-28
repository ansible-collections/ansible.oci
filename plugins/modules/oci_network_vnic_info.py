# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_network_vnic_info
short_description: Gather information about a VNIC
description:
  - Retrieve one VNIC by OCID.
version_added: "1.2.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  vnic_id:
    description:
      - The OCID of the VNIC.
      - Use M(ansible.oci.oci_vnic_attachment_info) to find the VNIC OCID.
    type: str
    required: true
"""

EXAMPLES = r"""
- name: Get a VNIC
  ansible.oci.oci_network_vnic_info:
    vnic_id: ocid1.vnic.oc1..example
  register: vnic_info
"""

RETURN = r"""
vnics:
  description: The requested VNIC, or an empty list when OCI returns HTTP 404.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The OCID of the VNIC.
      type: str
    name:
      description: The VNIC display name.
      type: str
    lifecycle_state:
      description: The VNIC lifecycle state.
      type: str
    nsg_ids:
      description: The VNIC network security groups.
      type: list
      elements: str
    hostname_label:
      description: The hostname label for the primary private IP.
      type: str
    skip_source_dest_check:
      description: Whether source and destination checks are disabled.
      type: bool
    route_table_id:
      description: The OCID of the VNIC route table.
      type: str
    security_attributes:
      description: Security attributes assigned to the VNIC.
      type: dict
    freeform_tags:
      description: Free-form tags assigned to the VNIC.
      type: dict
    defined_tags:
      description: Defined tags assigned to the VNIC.
      type: dict
    is_primary:
      description: Whether this VNIC is the primary VNIC of the instance.
      type: bool
    subnet_id:
      description: The subnet OCID for a VNIC in a subnet.
      type: str
    vlan_id:
      description: The VLAN OCID for a VNIC in a VLAN.
      type: str
    private_ip:
      description: The primary private IP address.
      type: str
    public_ip:
      description: The public IP address, when assigned.
      type: str
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import OciInfoBase

oci = import_oci_sdk()[0]


class OciNetworkVnicInfoModule(OciInfoBase):
    """Read one OCI VNIC by OCID."""

    @property
    def client_class(self):
        """Return the OCI virtual network client class.

        Returns:
            The SDK client class.
        """
        return oci.core.VirtualNetworkClient

    results_key = "vnics"
    resource_id_param = "vnic_id"
    resource_get_method = "get_vnic"


def main():
    """Run the VNIC info module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        vnic_id=dict(type="str", required=True),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    if not module.params.get("vnic_id"):
        module.fail_json(msg="vnic_id is required and cannot be empty")
    OciNetworkVnicInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
