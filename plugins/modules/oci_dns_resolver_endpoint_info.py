# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_dns_resolver_endpoint_info
short_description: Get information about DNS resolver endpoints
description:
  - Get one endpoint or list endpoints in an OCI DNS resolver.
version_added: "1.2.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  resolver_id:
    description: The OCID of the DNS resolver that contains the endpoint.
    type: str
    required: true
  name:
    description:
      - The name of one resolver endpoint to retrieve.
      - Omit this value to list endpoints in the resolver.
    type: str
"""

EXAMPLES = r"""
- name: List endpoints in a resolver
  ansible.oci.oci_dns_resolver_endpoint_info:
    resolver_id: ocid1.dnsresolver.oc1..example

- name: Get one endpoint
  ansible.oci.oci_dns_resolver_endpoint_info:
    resolver_id: ocid1.dnsresolver.oc1..example
    name: example_endpoint
"""

RETURN = r"""
endpoints:
  description: Resolver endpoints that match the query.
  returned: always
  type: list
  elements: dict
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import OciInfoBase

oci = import_oci_sdk()[0]


class OciDnsResolverEndpointInfoModule(OciInfoBase):
    """Get one or more endpoints from an OCI DNS resolver."""

    @property
    def client_class(self):
        """Return the OCI DNS service client class."""
        return oci.dns.DnsClient

    results_key = "endpoints"

    def fetch_resources(self):
        """Get an endpoint by name or list endpoints in the selected resolver.

        The inherited info lookup accepts one resource ID. Endpoint get
        requires the resolver ID and endpoint name, so this method overrides it.

        Returns:
            A list with the matching endpoint or all listed endpoints.
        """
        resolver_id = self.module.params.get("resolver_id")
        name = self.module.params.get("name")
        if name:
            return self.get_resource_by_id(
                name,
                self.client.get_resolver_endpoint,
                resolver_id=resolver_id,
                resolver_endpoint_name=name,
            )
        return self.list_all_resources(
            self.client.list_resolver_endpoints,
            resolver_id=resolver_id,
        )


def main():
    """Run the resolver endpoint info module."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        resolver_id=dict(type="str", required=True),
        name=dict(type="str"),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    OciDnsResolverEndpointInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
