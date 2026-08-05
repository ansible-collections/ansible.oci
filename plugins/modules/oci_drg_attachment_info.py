# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_drg_attachment_info
short_description: Retrieve DRG attachment information from Oracle Cloud Infrastructure
description:
  - Retrieve details about one or more OCI DRG attachments.
  - Use C(drg_attachment_id) to fetch a single attachment, or
    C(compartment_id) to list DRG attachments in a compartment.
  - This is a read-only module and does not modify resources.
version_added: "1.0.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - oracle.oci.oci_auth_options
options:
  compartment_id:
    description:
      - The OCID of the compartment to list DRG attachments from.
      - Required when listing resources.
    type: str
  drg_attachment_id:
    description:
      - The OCID of a specific DRG attachment to retrieve.
      - When specified, returns a single resource instead of a list.
    type: str
  drg_id:
    description:
      - Filter listed DRG attachments by DRG.
      - Only used when C(compartment_id) is provided.
    type: str
  vcn_id:
    description:
      - Filter listed DRG attachments by VCN.
      - Only used when C(compartment_id) is provided.
    type: str
  name:
    description:
      - Filter listed DRG attachments by name.
      - Only used when C(compartment_id) is provided.
    type: str
  lifecycle_state:
    description:
      - Filter listed DRG attachments by lifecycle state.
      - Only used when C(compartment_id) is provided.
    type: str
notes:
  - OCI's C(list_drg_attachments) operation lists only VCN attachments by
    default unless C(attachment_type=ALL) is supplied.
  - This module intentionally mirrors C(oracle.oci.oci_drg_attachment)'s
    VCN-only scope and therefore does not expose C(attachment_type) or
    C(network_id).
"""

EXAMPLES = r"""
- name: List all DRG attachments in a compartment
  oracle.oci.oci_drg_attachment_info:
    compartment_id: ocid1.compartment.oc1..example

- name: List DRG attachments for a specific DRG and VCN by name
  oracle.oci.oci_drg_attachment_info:
    compartment_id: ocid1.compartment.oc1..example
    drg_id: ocid1.drg.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    name: example-drg-attachment

- name: Get a specific DRG attachment
  oracle.oci.oci_drg_attachment_info:
    drg_attachment_id: ocid1.drgattachment.oc1..example
"""

RETURN = r"""
drg_attachments:
  description: List of DRG attachments that matched the query.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The OCID of the DRG attachment.
      type: str
      returned: always
      sample: ocid1.drgattachment.oc1..example
    name:
      description: The display name of the DRG attachment.
      type: str
      returned: always
      sample: example-drg-attachment
    compartment_id:
      description: The OCID of the compartment containing the DRG attachment.
      type: str
      returned: always
      sample: ocid1.compartment.oc1..example
    drg_id:
      description: The OCID of the attached DRG.
      type: str
      returned: always
      sample: ocid1.drg.oc1..example
    vcn_id:
      description: The OCID of the attached VCN.
      type: str
      returned: always
      sample: ocid1.vcn.oc1..example
    lifecycle_state:
      description: The current lifecycle state of the DRG attachment.
      type: str
      returned: always
      sample: ATTACHED
    route_table_id:
      description: The OCID of the VCN-side route table associated with the attachment, if any.
      type: str
      returned: always
      sample: null
    drg_route_table_id:
      description: The OCID of the DRG-side route table associated with the attachment, if any.
      type: str
      returned: always
      sample: null
    network_details:
      description: The attached network's details, as returned by OCI.
      type: dict
      returned: always
      sample: {"type": "VCN", "id": "ocid1.vcn.oc1..example"}
    export_drg_route_distribution_id:
      description: The OCID of the route distribution assigned to this attachment for exporting routes, if any.
      type: str
      returned: always
      sample: null
    is_cross_tenancy:
      description: Whether the attached network lives in a different tenancy than the DRG.
      type: bool
      returned: always
      sample: false
    freeform_tags:
      description: Free-form tags applied to the DRG attachment.
      type: dict
      returned: always
      sample: {"environment": "production"}
    defined_tags:
      description: Defined tags applied to the DRG attachment.
      type: dict
      returned: always
      sample: {"Operations": {"CostCenter": "42"}}
    time_created:
      description: The date and time the DRG attachment was created, in RFC3339 format.
      type: str
      returned: always
      sample: "2026-01-01T00:00:00.000Z"
  sample:
    - id: ocid1.drgattachment.oc1..example
      name: example-drg-attachment
      compartment_id: ocid1.compartment.oc1..example
      drg_id: ocid1.drg.oc1..example
      vcn_id: ocid1.vcn.oc1..example
      lifecycle_state: ATTACHED
      route_table_id: null
      drg_route_table_id: null
      network_details: {"type": "VCN", "id": "ocid1.vcn.oc1..example"}
      export_drg_route_distribution_id: null
      is_cross_tenancy: false
      freeform_tags: {"environment": "production"}
      defined_tags: {"Operations": {"CostCenter": "42"}}
      time_created: "2026-01-01T00:00:00.000Z"
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.oracle.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)
from ansible_collections.oracle.oci.plugins.module_utils.oci_info import (
    OciInfoBase,
)

imported_oci_sdk = import_oci_sdk()
oci = imported_oci_sdk[0]
HAS_OCI_SDK = imported_oci_sdk[1]


class OciDrgAttachmentInfoModule(OciInfoBase):
    """Concrete info adapter for OCI DRG attachments."""

    @property
    def client_class(self):
        return oci.core.VirtualNetworkClient

    results_key = "drg_attachments"
    resource_id_param = "drg_attachment_id"
    resource_get_method = "get_drg_attachment"
    list_resource_method = "list_drg_attachments"
    list_filter_params = [
        "compartment_id",
        "drg_id",
        "vcn_id",
        "lifecycle_state",
    ]


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        compartment_id=dict(type="str"),
        drg_attachment_id=dict(type="str"),
        drg_id=dict(type="str"),
        vcn_id=dict(type="str"),
        name=dict(type="str"),
        lifecycle_state=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["compartment_id", "drg_attachment_id"]],
    )

    OciDrgAttachmentInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
