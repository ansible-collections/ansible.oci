# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Discover OCI Compute App Catalog listings."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_app_catalog_info
short_description: Get OCI Compute App Catalog listings
description:
  - List published OCI Compute App Catalog listings or get one listing by OCID.
version_added: "1.3.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  listing_id:
    description:
      - The OCID of one listing to retrieve.
    type: str
  name:
    description:
      - Return listings with this exact display name.
      - This option applies to list operations.
    type: str
"""

EXAMPLES = r"""
- name: List App Catalog listings
  ansible.oci.oci_app_catalog_info: {}
  register: app_catalog_listings

- name: Find a listing by display name
  ansible.oci.oci_app_catalog_info:
    name: Oracle Linux

- name: Get one listing
  ansible.oci.oci_app_catalog_info:
    listing_id: ocid1.appcataloglisting.oc1..example
"""

RETURN = r"""
listings:
  description:
    - Listings that match the query.
    - List operations return summaries. Get operations return listing details.
  returned: always
  type: list
  elements: dict
  contains:
    listing_id:
      description: The OCID of the listing.
      type: str
      returned: always
      sample: ocid1.appcataloglisting.oc1..example
    name:
      description: The user-friendly listing name.
      type: str
      returned: always
      sample: Oracle Linux
    summary:
      description: A short summary of the listing.
      type: str
      returned: always
      sample: Oracle Linux image
    publisher_name:
      description: The listing publisher name.
      type: str
      returned: always
      sample: Oracle
    description:
      description: The full listing description.
      type: str
      returned: when a listing is fetched by ID
      sample: Oracle Linux compute image
    contact_url:
      description: The listing contact URL.
      type: str
      returned: when a listing is fetched by ID
      sample: https://www.oracle.com/linux/
    publisher_logo_url:
      description: The publisher logo URL.
      type: str
      returned: when a listing is fetched by ID
      sample: https://example.com/logo.png
    time_published:
      description: The publication time in RFC 3339 format.
      type: str
      returned: when a listing is fetched by ID
      sample: '2026-01-01T00:00:00+00:00'
  sample:
    - listing_id: ocid1.appcataloglisting.oc1..example
      name: Oracle Linux
      summary: Oracle Linux image
      publisher_name: Oracle
    - listing_id: ocid1.appcataloglisting.oc1..example
      name: Oracle Linux
      summary: Oracle Linux image
      publisher_name: Oracle
      description: Oracle Linux compute image
      contact_url: https://www.oracle.com/linux/
      publisher_logo_url: https://example.com/logo.png
      time_published: '2026-01-01T00:00:00+00:00'
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import OciInfoBase

oci = import_oci_sdk()[0]


class OciAppCatalogInfoModule(OciInfoBase):
    """Provide list and get operations for App Catalog listings."""
    @property
    def client_class(self):
        """Return the client class for Compute App Catalog operations.

        Returns:
            The OCI Compute client class.
        """
        return oci.core.ComputeClient

    results_key = "listings"
    resource_id_param = "listing_id"
    resource_get_method = "get_app_catalog_listing"
    list_resource_method = "list_app_catalog_listings"


def main():
    """Run the App Catalog listing info module."""
    module = AnsibleModule(
        argument_spec=dict(OCI_AUTH_ARGS, listing_id=dict(type="str"), name=dict(type="str")),
        mutually_exclusive=[["listing_id", "name"]],
        supports_check_mode=True,
    )
    OciAppCatalogInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
