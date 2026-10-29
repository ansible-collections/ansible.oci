# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_dns_zone_records_info
short_description: Retrieve records from an OCI DNS zone
description:
  - Return records from a DNS zone.
version_added: "1.2.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  zone_name_or_id:
    description: The name or OCID of the DNS zone.
    type: str
    required: true
  scope:
    description: The zone scope. A private zone name requires C(view_id).
    type: str
    choices:
      - global
      - private
  view_id:
    description: The OCID of the view for a private zone.
    type: str
  domain:
    description: Return records for this domain.
    type: str
  domain_contains:
    description: Return records with a domain that contains this text.
    type: str
  rtype:
    description:
      - Filter records by type. For example, C(A), C(AAAA), or C(CNAME).
      - The module accepts upper or lower case.
      - Supported types depend on the zone scope.
      - See L(public DNS record types,https://docs.oracle.com/en-us/iaas/Content/DNS/Reference/supporteddnsresource.htm).
      - See L(private DNS record types,https://docs.oracle.com/en-us/iaas/Content/DNS/Tasks/privatedns.htm).
    type: str
  zone_version:
    description: Return records for this zone version.
    type: str
  sort_by:
    description: Sort records by this field.
    type: str
    choices:
      - domain
      - rtype
      - ttl
  sort_order:
    description: The record sort order.
    type: str
    choices:
      - asc
      - desc
"""

EXAMPLES = r"""
- name: List all records in a DNS zone
  ansible.oci.oci_dns_zone_records_info:
    zone_name_or_id: example.com

- name: List A records for a domain
  ansible.oci.oci_dns_zone_records_info:
    zone_name_or_id: example.com
    domain: www.example.com
    rtype: a
"""

RETURN = r"""
records:
  description: Matching records. Each has domain, rtype, rdata, ttl, record_hash, is_protected, and rrset_version.
  returned: always
  type: list
  elements: dict
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_dns import (
    OciDnsRecordsInfo,
    build_dns_argument_spec,
)


class OciDnsZoneRecordsInfoModule(OciDnsRecordsInfo):
    """Retrieve records scoped to a DNS zone."""

    scope_kind = "zone"


def main():
    """Run the DNS zone record info module."""
    module = AnsibleModule(
        argument_spec=build_dns_argument_spec("zone", info=True),
        supports_check_mode=True,
    )
    OciDnsZoneRecordsInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
