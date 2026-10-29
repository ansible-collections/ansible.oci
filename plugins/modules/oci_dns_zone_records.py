# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_dns_zone_records
short_description: Manage DNS records in an OCI zone
description:
  - Set zone records to match C(update_items). Keep protected records.
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
  state:
    description:
      - The desired state of the zone record set.
      - Changes require the same OCI ETag on every page of the record collection.
      - The module fails if the ETag is missing or the records change after the read.
    type: str
    choices:
      - present
    default: present
  update_items:
    description:
      - The complete list of records to keep when C(state=present).
      - To update a record, include its new values and all other records to keep.
      - To delete a mutable record, omit it and include all other records to keep.
      - Protected records that are omitted remain unchanged.
      - Each item must contain C(domain), C(rtype), C(rdata), and C(ttl).
    type: list
    elements: dict
    suboptions:
      domain:
        description: The record domain name.
        type: str
        required: true
      rtype:
        description: The record type.
        type: str
        required: true
      rdata:
        description:
          - The record data in OCI DNS format.
          - OCI can normalize returned data. For idempotency, use the format that OCI returns.
        type: str
        required: true
      ttl:
        description: The record time to live in seconds.
        type: int
        required: true
"""

EXAMPLES = r"""
- name: Set records for a DNS zone
  ansible.oci.oci_dns_zone_records:
    zone_name_or_id: example.com
    update_items:
      - domain: www.example.com
        rtype: a
        rdata: 192.0.2.10
        ttl: 300
"""

RETURN = r"""
resource:
  description:
    The record set. Each item has domain, rtype, rdata, ttl, record_hash,
    is_protected, and rrset_version fields.
  returned: when state is present
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_dns import (
    OciDnsRecordsResource,
    build_dns_argument_spec,
)


class OciDnsZoneRecordsModule(OciDnsRecordsResource):
    """Manage records scoped to a DNS zone."""

    scope_kind = "zone"


def main():
    """Run the DNS zone record module."""
    argument_spec = build_dns_argument_spec("zone")
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[("state", "present", ["update_items"])],
    )
    OciDnsZoneRecordsModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
