# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_volume_attachment_info
short_description: Retrieve block volume attachment information from Oracle Cloud Infrastructure
description:
  - Retrieve details about one or more OCI block volume attachments.
  - Use C(volume_attachment_id) to fetch a single attachment, or
    C(compartment_id) to list attachments in a compartment.
  - This is a read-only module and does not modify resources.
version_added: "1.0.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  compartment_id:
    description:
      - The OCID of the compartment to list volume attachments from.
      - Required when listing resources.
    type: str
  volume_attachment_id:
    description:
      - The OCID of a specific volume attachment to retrieve.
      - When specified, returns a single resource instead of a list.
    type: str
  availability_domain:
    description:
      - Filter listed attachments by availability domain.
      - Only used when C(compartment_id) is provided.
    type: str
  instance_id:
    description:
      - Filter listed attachments by compute instance.
      - Only used when C(compartment_id) is provided.
    type: str
  volume_id:
    description:
      - Filter listed attachments by block volume.
      - Only used when C(compartment_id) is provided.
    type: str
  name:
    description:
      - Filter listed attachments by name.
      - Only used when C(compartment_id) is provided.
    type: str
"""

EXAMPLES = r"""
- name: List all volume attachments in a compartment
  ansible.oci.oci_volume_attachment_info:
    compartment_id: ocid1.compartment.oc1..example

- name: List volume attachments for a specific instance and volume by name
  ansible.oci.oci_volume_attachment_info:
    compartment_id: ocid1.compartment.oc1..example
    instance_id: ocid1.instance.oc1..example
    volume_id: ocid1.volume.oc1..example
    name: example-attachment

- name: Get a specific volume attachment
  ansible.oci.oci_volume_attachment_info:
    volume_attachment_id: ocid1.volumeattachment.oc1..example
"""

RETURN = r"""
volume_attachments:
  description: List of volume attachments that matched the query.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The OCID of the volume attachment.
      type: str
      returned: always
      sample: ocid1.volumeattachment.oc1..example
    name:
      description: The display name of the volume attachment.
      type: str
      returned: always
      sample: example-attachment
    compartment_id:
      description: The OCID of the compartment containing the attachment.
      type: str
      returned: always
      sample: ocid1.compartment.oc1..example
    availability_domain:
      description: The availability domain of the attachment.
      type: str
      returned: always
      sample: Uocm:PHX-AD-1
    instance_id:
      description: The OCID of the attached compute instance.
      type: str
      returned: always
      sample: ocid1.instance.oc1..example
    volume_id:
      description: The OCID of the attached block volume.
      type: str
      returned: always
      sample: ocid1.volume.oc1..example
    attachment_type:
      description: The attachment type as returned by OCI.
      type: str
      returned: always
      sample: paravirtualized
    lifecycle_state:
      description: The current lifecycle state of the attachment.
      type: str
      returned: always
      sample: ATTACHED
    device:
      description: The device name the volume is exposed as on the instance, if any.
      type: str
      returned: always
      sample: /dev/oracleoci/oraclevdb
    is_read_only:
      description: Whether the volume is attached read-only.
      type: bool
      returned: always
      sample: false
    is_shareable:
      description: Whether the attachment is shareable across instances.
      type: bool
      returned: always
      sample: false
    ipv4:
      description: The IPv4 address of the iSCSI target, when C(attachment_type) is C(iscsi).
      type: str
      returned: when attachment_type is iscsi
      sample: 10.0.0.12
    iqn:
      description: The iSCSI qualified name of the target, when C(attachment_type) is C(iscsi).
      type: str
      returned: when attachment_type is iscsi
      sample: iqn.2015-12.com.oracleiaas:example
    port:
      description: The iSCSI target port, when C(attachment_type) is C(iscsi).
      type: int
      returned: when attachment_type is iscsi
      sample: 3260
    iscsi_login_state:
      description: The iSCSI login state of the attachment, when C(attachment_type) is C(iscsi).
      type: str
      returned: when attachment_type is iscsi
      sample: LOGIN_SUCCEEDED
    encryption_in_transit_type:
      description: The iSCSI encryption-in-transit mode, when C(attachment_type) is C(iscsi).
      type: str
      returned: when attachment_type is iscsi
      sample: NONE
    is_pv_encryption_in_transit_enabled:
      description: Whether in-transit encryption is enabled for a paravirtualized attachment.
      type: bool
      returned: when attachment_type is paravirtualized
      sample: false
    time_created:
      description: The date and time the attachment was created, in RFC3339 format.
      type: str
      returned: always
      sample: "2026-01-01T00:00:00.000Z"
  sample:
    - id: ocid1.volumeattachment.oc1..example
      name: example-attachment
      compartment_id: ocid1.compartment.oc1..example
      availability_domain: Uocm:PHX-AD-1
      instance_id: ocid1.instance.oc1..example
      volume_id: ocid1.volume.oc1..example
      attachment_type: paravirtualized
      lifecycle_state: ATTACHED
      device: /dev/oracleoci/oraclevdb
      is_read_only: false
      is_shareable: false
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

imported_oci_sdk = import_oci_sdk()
oci = imported_oci_sdk[0]
HAS_OCI_SDK = imported_oci_sdk[1]


class OciVolumeAttachmentInfoModule(OciInfoBase):
    """Concrete info adapter for OCI block volume attachments."""

    @property
    def client_class(self):
        return oci.core.ComputeClient

    results_key = "volume_attachments"
    resource_id_param = "volume_attachment_id"
    resource_get_method = "get_volume_attachment"
    list_resource_method = "list_volume_attachments"
    redacted_result_keys = ("chap_username", "chap_secret")
    list_filter_params = [
        "compartment_id",
        "availability_domain",
        "instance_id",
        "volume_id",
    ]


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        compartment_id=dict(type="str"),
        volume_attachment_id=dict(type="str"),
        availability_domain=dict(type="str"),
        instance_id=dict(type="str"),
        volume_id=dict(type="str"),
        name=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["compartment_id", "volume_attachment_id"]],
    )

    OciVolumeAttachmentInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
