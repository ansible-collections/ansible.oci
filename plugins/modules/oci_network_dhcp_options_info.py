# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_network_dhcp_options_info
short_description: Retrieve DHCP Options information from Oracle Cloud Infrastructure
description:
  - Retrieve details about one or more OCI VCN DHCP options sets.
  - Use C(dhcp_options_id) to fetch a single DHCP options set, or
    C(compartment_id) to list DHCP options in a compartment.
  - This is a read-only module and does not modify resources.
version_added: "1.0.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_info_filter_options
options:
  compartment_id:
    description:
      - The OCID of the compartment to list DHCP options from.
      - Required when listing resources.
    type: str
  dhcp_options_id:
    description:
      - The OCID of a specific DHCP options set to retrieve.
      - When specified, returns a single resource instead of a list.
    type: str
  vcn_id:
    description:
      - Filter listed DHCP options by VCN.
      - Only used when C(compartment_id) is provided.
    type: str
notes:
  - Each returned C(options) entry uses the same C(option_type)/
    C(server_type) snake_case vocabulary accepted by
    C(ansible.oci.oci_network_dhcp_options), translated from OCI's native enum
    casing.
  - The returned C(domain_name_type) uses this same snake_case vocabulary,
    also translated from OCI's native enum casing.
"""

EXAMPLES = r"""
- name: List all DHCP options in a compartment
  ansible.oci.oci_network_dhcp_options_info:
    compartment_id: ocid1.compartment.oc1..example

- name: List DHCP options in a VCN by name
  ansible.oci.oci_network_dhcp_options_info:
    compartment_id: ocid1.compartment.oc1..example
    vcn_id: ocid1.vcn.oc1..example
    name: example-dhcp-options

- name: Get a specific DHCP options set
  ansible.oci.oci_network_dhcp_options_info:
    dhcp_options_id: ocid1.dhcpoptions.oc1..example
"""

RETURN = r"""
dhcp_options:
  description: List of DHCP options sets that matched the query.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: The OCID of the DHCP options.
      type: str
      returned: always
      sample: ocid1.dhcpoptions.oc1..example
    name:
      description: The display name of the DHCP options.
      type: str
      returned: always
      sample: example-dhcp-options
    compartment_id:
      description: The OCID of the compartment containing the DHCP options.
      type: str
      returned: always
      sample: ocid1.compartment.oc1..example
    vcn_id:
      description: The OCID of the VCN containing the DHCP options.
      type: str
      returned: always
      sample: ocid1.vcn.oc1..example
    lifecycle_state:
      description: The current lifecycle state of the DHCP options.
      type: str
      returned: always
      sample: AVAILABLE
    options:
      description: >-
        The DHCP options, using the same C(option_type)/C(server_type)
        snake_case vocabulary accepted as input by ansible.oci.oci_network_dhcp_options.
      type: list
      elements: dict
      returned: always
      sample:
        - option_type: domain_name_server
          server_type: vcn_local_plus_internet
        - option_type: search_domain
          search_domain_names:
            - example.oraclevcn.com
    domain_name_type:
      description: The domain name type used for the VCN.
      type: str
      returned: always
      sample: SUBNET_DOMAIN
    freeform_tags:
      description: Free-form tags applied to the DHCP options.
      type: dict
      returned: always
      sample: {"environment": "production"}
    defined_tags:
      description: Defined tags applied to the DHCP options.
      type: dict
      returned: always
      sample: {"Operations": {"CostCenter": "42"}}
    time_created:
      description: The date and time the DHCP options were created, in RFC3339 format.
      type: str
      returned: always
      sample: "2026-01-01T00:00:00.000Z"
  sample:
    - id: ocid1.dhcpoptions.oc1..example
      name: example-dhcp-options
      compartment_id: ocid1.compartment.oc1..example
      vcn_id: ocid1.vcn.oc1..example
      lifecycle_state: AVAILABLE
      options:
        - option_type: domain_name_server
          server_type: vcn_local_plus_internet
        - option_type: search_domain
          search_domain_names:
            - example.oraclevcn.com
      domain_name_type: SUBNET_DOMAIN
      freeform_tags: {"environment": "production"}
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

imported_oci_sdk = import_oci_sdk()
oci = imported_oci_sdk[0]
HAS_OCI_SDK = imported_oci_sdk[1]

# Mirrors the translation tables in oci_dhcp_options.py. Kept local rather
# than imported, matching this collection's convention of self-contained
# module files (each plugins/modules/*.py stands alone).
OPTION_TYPE_TO_OCI = {
    "domain_name_server": "DomainNameServer",
    "search_domain": "SearchDomain",
}
OCI_OPTION_TYPE_TO_ANSIBLE = {
    oci_value: ansible_value for ansible_value, oci_value in OPTION_TYPE_TO_OCI.items()
}

SERVER_TYPE_TO_OCI = {
    "vcn_local": "VcnLocal",
    "vcn_local_plus_internet": "VcnLocalPlusInternet",
    "custom_dns_server": "CustomDnsServer",
}
OCI_SERVER_TYPE_TO_ANSIBLE = {
    oci_value: ansible_value for ansible_value, oci_value in SERVER_TYPE_TO_OCI.items()
}

DOMAIN_NAME_TYPE_TO_OCI = {
    "subnet_domain": "SUBNET_DOMAIN",
    "vcn_domain": "VCN_DOMAIN",
    "custom_domain": "CUSTOM_DOMAIN",
}
OCI_DOMAIN_NAME_TYPE_TO_ANSIBLE = {
    oci_value: ansible_value for ansible_value, oci_value in DOMAIN_NAME_TYPE_TO_OCI.items()
}


def normalize_result_option(option):
    """Translate one serialized DhcpOption dict to the ansible-facing shape.

    See the matching helper in oci_dhcp_options.py for the full rationale:
    this renames ``type`` to ``option_type`` and translates both
    ``option_type`` and ``server_type`` out of OCI's native enum casing.
    """
    if not isinstance(option, dict):
        return option

    normalized = dict(option)
    oci_type = normalized.pop("type", None)
    normalized["option_type"] = OCI_OPTION_TYPE_TO_ANSIBLE.get(oci_type, oci_type)
    if "server_type" in normalized:
        normalized["server_type"] = OCI_SERVER_TYPE_TO_ANSIBLE.get(
            normalized["server_type"], normalized["server_type"]
        )
    return normalized


def normalize_result_options(options):
    return [normalize_result_option(option) for option in (options or [])]


class OciNetworkDhcpOptionsInfoModule(OciInfoBase):
    """Concrete info adapter for OCI VCN DHCP options."""

    @property
    def client_class(self):
        return oci.core.VirtualNetworkClient

    results_key = "dhcp_options"
    resource_id_param = "dhcp_options_id"
    resource_id_kwarg = "dhcp_id"
    resource_get_method = "get_dhcp_options"
    list_resource_method = "list_dhcp_options"
    list_filter_params = [
        "compartment_id",
        "vcn_id",
        "lifecycle_state",
    ]

    def serialize_result_resource(self, resource):
        result = super().serialize_result_resource(resource)
        if isinstance(result, dict):
            if "options" in result:
                result["options"] = normalize_result_options(result["options"])
            if "domain_name_type" in result:
                result["domain_name_type"] = OCI_DOMAIN_NAME_TYPE_TO_ANSIBLE.get(
                    result["domain_name_type"], result["domain_name_type"]
                )
        return result


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        compartment_id=dict(type="str"),
        dhcp_options_id=dict(type="str"),
        vcn_id=dict(type="str"),
        name=dict(type="str"),
        lifecycle_state=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[["compartment_id", "dhcp_options_id"]],
    )

    OciNetworkDhcpOptionsInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
