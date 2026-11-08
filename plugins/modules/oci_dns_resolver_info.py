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
  description:
    - The resolvers that match the request.
    - Compartment list requests return summary records.
    - Requests with C(resolver_id) also return endpoints, attached views, and rules.
  returned: always
  type: list
  elements: dict
  contains:
    compartment_id:
      description: The OCID of the compartment that contains the resolver.
      type: str
      returned: when available
    attached_vcn_id:
      description: The OCID of the virtual cloud network attached to the resolver.
      type: str
      returned: when available
    name:
      description: The display name of the resolver, returned as C(name).
      type: str
      returned: when available
    freeform_tags:
      description: The free-form tags applied to the resolver.
      type: dict
      returned: when available
    defined_tags:
      description: The defined tags applied to the resolver.
      type: dict
      returned: when available
    id:
      description: The OCID of the resolver.
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
      description: The current lifecycle state of the resolver.
      type: str
      returned: when available
    _self:
      description: The URL of the resolver resource.
      type: str
      returned: when available
    default_view_id:
      description: The OCID of the default DNS view for the resolver.
      type: str
      returned: when available
    is_protected:
      description: Whether the resolver is protected from deletion.
      type: bool
      returned: when available
    endpoints:
      description: The endpoint summaries for the resolver.
      type: list
      returned: when resolver_id is specified
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
    attached_views:
      description: The DNS views attached to the resolver.
      type: list
      returned: when resolver_id is specified
      elements: dict
      contains:
        view_id:
          description: The OCID of the attached DNS view.
          type: str
          returned: when available
    rules:
      description: The forwarding rules applied to the resolver.
      type: list
      returned: when resolver_id is specified
      elements: dict
      contains:
        client_address_conditions:
          description: The client IP addresses or CIDR ranges that match the rule.
          type: list
          returned: when available
          elements: str
        qname_cover_conditions:
          description: The DNS query names that match the rule.
          type: list
          returned: when available
          elements: str
        action:
          description: The rule action. Forwarding rules return C(FORWARD).
          type: str
          returned: when available
        destination_addresses:
          description: The destination IP addresses for forwarded DNS queries.
          type: list
          returned: when available
          elements: str
        source_endpoint_name:
          description: The name of the endpoint used to forward DNS queries.
          type: str
          returned: when available
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
