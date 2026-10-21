# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_bastion_info
short_description: Retrieve bastion information from Oracle Cloud Infrastructure
description:
  - Retrieve details about one or more OCI bastions.
  - Use C(bastion_id) to fetch a single bastion, or C(compartment_id) to list
    bastions in a compartment.
  - This is a read-only module and does not modify resources.
version_added: "1.1.0"
author:
  - Mike Morency (@mikemorency)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  compartment_id:
    description:
      - The OCID of the compartment to list bastions from.
      - Required when listing resources.
    type: str
  bastion_id:
    description:
      - The OCID of a specific bastion to retrieve.
      - When specified, returns a single resource instead of a list.
    type: str
  name:
    description:
      - Filter listed bastions by name.
      - Only used when C(compartment_id) is provided.
    type: str
  bastion_lifecycle_state:
    description:
      - Filter listed bastions by lifecycle state.
      - Only used when C(compartment_id) is provided.
    type: str
"""

EXAMPLES = r"""
- name: List bastions in a compartment
  ansible.oci.oci_bastion_info:
    compartment_id: ocid1.compartment.oc1..example

- name: List active bastions in a compartment by name
  ansible.oci.oci_bastion_info:
    compartment_id: ocid1.compartment.oc1..example
    name: example-bastion
    bastion_lifecycle_state: ACTIVE

- name: Get a specific bastion
  ansible.oci.oci_bastion_info:
    bastion_id: ocid1.bastion.oc1..example
"""

RETURN = r"""
bastions:
  description: List of bastions that matched the query.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The OCID of the bastion.
      type: str
      returned: always
      sample: ocid1.bastion.oc1..example
    name:
      description: The name of the bastion.
      type: str
      returned: always
      sample: example-bastion
    bastion_type:
      description: The type of the bastion.
      type: str
      returned: always
      sample: standard
    compartment_id:
      description: The OCID of the compartment containing the bastion.
      type: str
      returned: always
      sample: ocid1.compartment.oc1..example
    target_vcn_id:
      description: The OCID of the VCN the bastion connects sessions to.
      type: str
      returned: always
      sample: ocid1.vcn.oc1..example
    target_subnet_id:
      description: The OCID of the subnet the bastion connects sessions to.
      type: str
      returned: always
      sample: ocid1.subnet.oc1..example
    lifecycle_state:
      description: The current lifecycle state of the bastion.
      type: str
      returned: always
      sample: ACTIVE
    lifecycle_details:
      description: A message describing the current lifecycle state in detail.
      type: str
      returned: always
      sample: null
    dns_proxy_status:
      description: The DNS proxy status of the bastion.
      type: str
      returned: always
      sample: DISABLED
    client_cidr_block_allow_list:
      description: The address ranges allowed to connect to sessions.
      type: list
      elements: str
      returned: always
      sample: ["0.0.0.0/0"]
    static_jump_host_ip_addresses:
      description: The IP addresses of the hosts the bastion has access to.
      type: list
      elements: str
      returned: always
      sample: []
    max_session_ttl_in_seconds:
      description: The maximum lifetime, in seconds, of a session on the bastion.
      type: int
      returned: always
      sample: 1800
    max_sessions_allowed:
      description: The maximum number of concurrent sessions allowed on the bastion.
      type: int
      returned: always
      sample: 10
    private_endpoint_ip_address:
      description: The private IP address of the bastion's endpoint in the subnet.
      type: str
      returned: always
      sample: 10.0.1.5
    freeform_tags:
      description: Free-form tags applied to the bastion.
      type: dict
      returned: always
      sample: {"environment": "production"}
    defined_tags:
      description: Defined tags applied to the bastion.
      type: dict
      returned: always
      sample: {"Operations": {"CostCenter": "42"}}
    security_attributes:
      description: Zero Trust Packet Routing security attributes applied to the bastion.
      type: dict
      returned: always
      sample: {}
    system_tags:
      description: System tags applied to the bastion by OCI.
      type: dict
      returned: always
      sample: {}
    time_created:
      description: The date and time the bastion was created, in RFC3339 format.
      type: str
      returned: always
      sample: "2026-01-01T00:00:00.000Z"
    time_updated:
      description: The date and time the bastion was last updated, in RFC3339 format.
      type: str
      returned: always
      sample: "2026-01-01T00:00:00.000Z"
  sample:
    - id: ocid1.bastion.oc1..example
      name: example-bastion
      bastion_type: standard
      compartment_id: ocid1.compartment.oc1..example
      target_vcn_id: ocid1.vcn.oc1..example
      target_subnet_id: ocid1.subnet.oc1..example
      lifecycle_state: ACTIVE
      dns_proxy_status: DISABLED
      client_cidr_block_allow_list: ["0.0.0.0/0"]
      max_session_ttl_in_seconds: 1800
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


class OciBastionInfoModule(OciInfoBase):
    """Concrete info adapter for OCI bastions."""

    @property
    def client_class(self):
        return oci.bastion.BastionClient

    results_key = "bastions"
    resource_id_param = "bastion_id"
    resource_get_method = "get_bastion"
    list_resource_method = "list_bastions"
    list_filter_params = [
        "compartment_id",
        "bastion_lifecycle_state",
    ]
    # The Bastion SDK model exposes its display field as ``name`` rather than the
    # ``display_name`` used by most OCI resources, so local name filtering must
    # resolve against ``name``.
    name_filter_param = "name"
    name_response_field = "name"


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        compartment_id=dict(type="str"),
        bastion_id=dict(type="str"),
        name=dict(type="str"),
        bastion_lifecycle_state=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["compartment_id", "bastion_id"]],
    )

    OciBastionInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
