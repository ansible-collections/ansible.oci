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
  description:
    - The resolver endpoints that match the request.
    - List requests return summary records.
    - Requests with C(name) also return fields specific to the endpoint type.
  returned: always
  type: list
  elements: dict
  contains:
    name:
      description: The endpoint name within the resolver.
      type: str
      returned: when available
    endpoint_type:
      description: The endpoint type. VNIC identifies an endpoint with a virtual network interface.
      type: str
      returned: when available
    forwarding_address:
      description: The IPv4 address used to forward DNS queries.
      type: str
      returned: when available
    is_forwarding:
      description: Whether the endpoint forwards DNS queries.
      type: bool
      returned: when available
    is_listening:
      description: Whether the endpoint listens for DNS queries.
      type: bool
      returned: when available
    listening_address:
      description: The IPv4 address used to receive DNS queries.
      type: str
      returned: when available
    id:
      description: The OCID of the endpoint.
      type: str
      returned: when available
    resolver_id:
      description: The OCID of the resolver that contains the endpoint.
      type: str
      returned: when available
    compartment_id:
      description: The OCID of the compartment that contains the endpoint.
      type: str
      returned: when available
    time_created:
      description: The creation time in RFC 3339 format.
      type: str
      returned: when available
    time_updated:
      description: The last update time in RFC 3339 format.
      type: str
      returned: when available
    lifecycle_state:
      description: The current lifecycle state of the endpoint.
      type: str
      returned: when available
    _self:
      description: The URL of the endpoint resource.
      type: str
      returned: when available
    freeform_tags:
      description: The free-form tags applied to the endpoint.
      type: dict
      returned: when available
    defined_tags:
      description: The defined tags applied to the endpoint.
      type: dict
      returned: when available
    subnet_id:
      description: The OCID of the subnet that contains the endpoint interface.
      type: str
      returned: when name is specified and the endpoint type is VNIC
    nsg_ids:
      description: The network security group OCIDs for the endpoint interface.
      type: list
      returned: when name is specified and the endpoint type is VNIC
      elements: str
    security_attributes:
      description: The security attributes applied to the endpoint.
      type: dict
      returned: when name is specified and the endpoint type is VNIC
    pe_id:
      description: The OCID of the private endpoint.
      type: str
      returned: when name is specified and the endpoint type is VNIC
    vnic_id:
      description: The OCID of the virtual network interface for the endpoint.
      type: str
      returned: when name is specified and the endpoint type is VNIC
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
