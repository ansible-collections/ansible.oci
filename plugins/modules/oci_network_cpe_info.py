# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: oci_network_cpe_info
short_description: Retrieve OCI customer-premises equipment information
description:
- Retrieve one CPE by OCID or list CPE objects in a compartment.
version_added: 1.2.0
author:
- Ron Gershburg (@ronger4)
extends_documentation_fragment:
- ansible.oci.oci_auth_options
options:
  compartment_id:
    description: The compartment OCID used for a list operation.
    type: str
  cpe_id:
    description: The OCID of one CPE to retrieve.
    type: str
  name:
    description: Filter listed CPEs by display name.
    type: str
"""

EXAMPLES = r"""
- name: Get one CPE
  ansible.oci.oci_network_cpe_info:
    cpe_id: ocid1.cpe.oc1..example

- name: List CPEs by name
  ansible.oci.oci_network_cpe_info:
    compartment_id: ocid1.compartment.oc1..example
    name: example-cpe
"""

RETURN = r"""
cpes:
  description: CPE objects that match the query.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The OCID of the CPE.
      type: str
    name:
      description: The display name of the CPE.
      type: str
    compartment_id:
      description: The CPE compartment OCID.
      type: str
    ip_address:
      description: The on-premises router IP address.
      type: str
    cpe_device_shape_id:
      description: The CPE device shape OCID.
      type: str
    freeform_tags:
      description: Free-form tags applied to the CPE.
      type: dict
    defined_tags:
      description: Defined tags applied to the CPE.
      type: dict
    time_created:
      description: The creation time in RFC3339 format.
      type: str
    is_private:
      description: Whether the CPE represents a private endpoint.
      type: bool
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import OciInfoBase

oci = import_oci_sdk()[0]


class OciNetworkCpeInfoModule(OciInfoBase):
    """Retrieve OCI CPE resources."""

    @property
    def client_class(self):
        """Return the OCI virtual network client class.

        Returns:
            The SDK client class.
        """
        return oci.core.VirtualNetworkClient

    results_key = "cpes"
    resource_id_param = "cpe_id"
    resource_get_method = "get_cpe"
    list_resource_method = "list_cpes"
    list_filter_params = ("compartment_id",)


def main():
    """Initialize and run the CPE info module."""
    module = AnsibleModule(
        argument_spec=dict(
            OCI_AUTH_ARGS,
            compartment_id=dict(type="str"),
            cpe_id=dict(type="str"),
            name=dict(type="str"),
        ),
        supports_check_mode=True,
        required_one_of=[["compartment_id", "cpe_id"]],
    )
    OciNetworkCpeInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
