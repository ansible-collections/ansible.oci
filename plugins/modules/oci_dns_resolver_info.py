# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_dns_resolver_info
short_description: Get DNS resolver information from Oracle Cloud Infrastructure
description:
  - Get one DNS resolver by its OCID or list resolvers in a compartment.
version_added: "1.2.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  resolver_id:
    description:
      - The OCID of a resolver to retrieve.
    type: str
  compartment_id:
    description:
      - The OCID of a compartment for a resolver list request.
    type: str
  name:
    description:
      - Filter listed resolvers by display name.
    type: str
"""

EXAMPLES = r"""
- name: Get one resolver
  ansible.oci.oci_dns_resolver_info:
    resolver_id: ocid1.dnsresolver.oc1..example

- name: List resolvers in a compartment
  ansible.oci.oci_dns_resolver_info:
    compartment_id: ocid1.compartment.oc1..example
"""

RETURN = r"""
resolvers:
  description: Resolvers that matched the request.
  returned: always
  type: list
  elements: dict
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import OCI_AUTH_ARGS, import_oci_sdk
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import OciInfoBase

oci = import_oci_sdk()[0]


class OciDnsResolverInfoModule(OciInfoBase):
    """Fetch DNS resolvers through the shared info helper."""

    @property
    def client_class(self):
        return oci.dns.DnsClient

    results_key = "resolvers"
    resource_id_param = "resolver_id"
    resource_get_method = "get_resolver"
    list_resource_method = "list_resolvers"
    list_filter_params = ("compartment_id",)


def main():
    """Run the resolver info module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        resolver_id=dict(type="str"),
        compartment_id=dict(type="str"),
        name=dict(type="str"),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )
    OciDnsResolverInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
