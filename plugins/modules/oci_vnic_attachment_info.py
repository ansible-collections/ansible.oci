# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_vnic_attachment_info
short_description: Retrieve VNIC attachment information from Oracle Cloud Infrastructure
description:
  - Retrieve one VNIC attachment by OCID or list attachments in a compartment.
  - List results can be filtered by availability domain, compute instance,
    VNIC, or attachment name.
  - This module is read-only and does not return the underlying VNIC resource.
version_added: "1.1.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  compartment_id:
    description:
      - The OCID of the compartment from which to list VNIC attachments.
      - Required when C(vnic_attachment_id) is not provided.
    type: str
  vnic_attachment_id:
    description:
      - The OCID of a specific VNIC attachment to retrieve.
    type: str
  availability_domain:
    description:
      - Filter listed attachments by availability domain.
    type: str
  instance_id:
    description:
      - Filter listed attachments by compute instance OCID.
    type: str
  vnic_id:
    description:
      - Filter listed attachments by VNIC OCID.
    type: str
  name:
    description:
      - Filter listed attachments locally by attachment display name.
    type: str
"""

EXAMPLES = r"""
- name: Get one VNIC attachment
  ansible.oci.oci_vnic_attachment_info:
    vnic_attachment_id: ocid1.vnicattachment.oc1..example

- name: List an instance's VNIC attachments
  ansible.oci.oci_vnic_attachment_info:
    compartment_id: ocid1.compartment.oc1..example
    instance_id: ocid1.instance.oc1..example

- name: Find a named attachment on an instance
  ansible.oci.oci_vnic_attachment_info:
    compartment_id: ocid1.compartment.oc1..example
    instance_id: ocid1.instance.oc1..example
    name: example-vnic-attachment
"""

RETURN = r"""
vnic_attachments:
  description: VNIC attachments matching the query.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The OCID of the VNIC attachment.
      type: str
      sample: ocid1.vnicattachment.oc1..example
    name:
      description: The display name of the VNIC attachment.
      type: str
      sample: example-vnic-attachment
    compartment_id:
      description: The OCID of the attachment compartment.
      type: str
      sample: ocid1.compartment.oc1..example
    availability_domain:
      description: The availability domain of the instance.
      type: str
      sample: Uocm:PHX-AD-1
    instance_id:
      description: The OCID of the compute instance.
      type: str
      sample: ocid1.instance.oc1..example
    lifecycle_state:
      description: The lifecycle state of the attachment.
      type: str
      sample: ATTACHED
    nic_index:
      description: The physical NIC index used by the VNIC.
      type: int
      sample: 0
    subnet_id:
      description: The OCID of the VNIC subnet, when applicable.
      type: str
      sample: ocid1.subnet.oc1..example
    vlan_id:
      description: The OCID of the VNIC VLAN, when applicable.
      type: str
      sample: ocid1.vlan.oc1..example
    vnic_id:
      description: The OCID of the VNIC.
      type: str
      sample: ocid1.vnic.oc1..example
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import (
    OciInfoBase,
)

imported_oci_sdk = import_oci_sdk()
oci = imported_oci_sdk[0]
HAS_OCI_SDK = imported_oci_sdk[1]


class OciVnicAttachmentInfoModule(OciInfoBase):
    """Concrete info adapter for OCI VNIC attachments."""

    @property
    def client_class(self):
        return oci.core.ComputeClient

    results_key = "vnic_attachments"
    resource_id_param = "vnic_attachment_id"
    resource_get_method = "get_vnic_attachment"
    list_resource_method = "list_vnic_attachments"
    list_filter_params = [
        "compartment_id",
        "availability_domain",
        "instance_id",
        "vnic_id",
    ]


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        compartment_id=dict(type="str"),
        vnic_attachment_id=dict(type="str"),
        availability_domain=dict(type="str"),
        instance_id=dict(type="str"),
        vnic_id=dict(type="str"),
        name=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["compartment_id", "vnic_attachment_id"]],
    )

    OciVnicAttachmentInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
