# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_network_drg_info
short_description: Retrieve Dynamic Routing Gateway (DRG) information from Oracle Cloud Infrastructure
description:
  - Retrieve details about one or more OCI Dynamic Routing Gateways (DRGs).
  - Use C(drg_id) to fetch a single DRG, or C(compartment_id) to list DRGs in
    a compartment.
  - This is a read-only module and does not modify resources.
version_added: "1.0.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - oracle.oci.oci_auth_options
options:
  compartment_id:
    description:
      - The OCID of the compartment to list DRGs from.
      - Required when listing resources.
    type: str
  drg_id:
    description:
      - The OCID of a specific DRG to retrieve.
      - When specified, returns a single resource instead of a list.
    type: str
  name:
    description:
      - Filter listed DRGs by name.
      - Only used when C(compartment_id) is provided.
    type: str
"""

EXAMPLES = r"""
- name: List all DRGs in a compartment
  oracle.oci.oci_network_drg_info:
    compartment_id: ocid1.compartment.oc1..example

- name: List DRGs in a compartment by name
  oracle.oci.oci_network_drg_info:
    compartment_id: ocid1.compartment.oc1..example
    name: example-drg

- name: Get a specific DRG
  oracle.oci.oci_network_drg_info:
    drg_id: ocid1.drg.oc1..example
"""

RETURN = r"""
drgs:
  description: List of DRGs that matched the query.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The OCID of the DRG.
      type: str
      returned: always
      sample: ocid1.drg.oc1..example
    name:
      description: The display name of the DRG.
      type: str
      returned: always
      sample: example-drg
    compartment_id:
      description: The OCID of the compartment containing the DRG.
      type: str
      returned: always
      sample: ocid1.compartment.oc1..example
    lifecycle_state:
      description: The current lifecycle state of the DRG.
      type: str
      returned: always
      sample: AVAILABLE
    default_drg_route_tables:
      description: >-
        The OCIDs of the default DRG route tables OCI creates automatically
        for each attachment type, keyed by attachment type.
      type: dict
      returned: always
      contains:
        vcn:
          description: The OCID of the default DRG route table for VCN attachments.
          type: str
          returned: always
          sample: ocid1.drgroutetable.oc1..vcn-example
        ipsec_tunnel:
          description: The OCID of the default DRG route table for IPSec tunnel attachments.
          type: str
          returned: always
          sample: ocid1.drgroutetable.oc1..ipsec-example
        virtual_circuit:
          description: The OCID of the default DRG route table for virtual circuit attachments.
          type: str
          returned: always
          sample: ocid1.drgroutetable.oc1..vc-example
        remote_peering_connection:
          description: The OCID of the default DRG route table for remote peering connection attachments.
          type: str
          returned: always
          sample: ocid1.drgroutetable.oc1..rpc-example
    default_export_drg_route_distribution_id:
      description: The OCID of the default export route distribution OCI creates automatically for the DRG.
      type: str
      returned: always
      sample: ocid1.drgroutedistribution.oc1..example
    freeform_tags:
      description: Free-form tags applied to the DRG.
      type: dict
      returned: always
      sample: {"environment": "production"}
    defined_tags:
      description: Defined tags applied to the DRG.
      type: dict
      returned: always
      sample: {"Operations": {"CostCenter": "42"}}
    time_created:
      description: The date and time the DRG was created, in RFC3339 format.
      type: str
      returned: always
      sample: "2026-01-01T00:00:00.000Z"
  sample:
    - id: ocid1.drg.oc1..example
      name: example-drg
      compartment_id: ocid1.compartment.oc1..example
      lifecycle_state: AVAILABLE
      default_drg_route_tables:
        vcn: ocid1.drgroutetable.oc1..vcn-example
        ipsec_tunnel: ocid1.drgroutetable.oc1..ipsec-example
        virtual_circuit: ocid1.drgroutetable.oc1..vc-example
        remote_peering_connection: ocid1.drgroutetable.oc1..rpc-example
      default_export_drg_route_distribution_id: ocid1.drgroutedistribution.oc1..example
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


class OciNetworkDrgInfoModule(OciInfoBase):
    """Concrete info adapter for OCI DRGs."""

    @property
    def client_class(self):
        return oci.core.VirtualNetworkClient

    results_key = "drgs"
    resource_id_param = "drg_id"
    resource_get_method = "get_drg"
    list_resource_method = "list_drgs"
    list_filter_params = [
        "compartment_id",
    ]


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        compartment_id=dict(type="str"),
        drg_id=dict(type="str"),
        name=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["compartment_id", "drg_id"]],
    )

    OciNetworkDrgInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
