# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Discover OCI Compute App Catalog listing resource versions."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_app_catalog_resource_version_info
short_description: Get OCI Compute App Catalog listing resource versions
description:
  - List resource versions for an App Catalog listing or get one version.
version_added: "1.3.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
options:
  listing_id:
    description:
      - The OCID of the App Catalog listing.
    type: str
    required: true
  listing_resource_version:
    description:
      - The version to retrieve.
      - Omit this option to list all versions.
    type: str
"""

EXAMPLES = r"""
- name: List listing resource versions
  ansible.oci.oci_app_catalog_resource_version_info:
    listing_id: ocid1.appcataloglisting.oc1..example
  register: listing_versions

- name: Get one listing resource version
  ansible.oci.oci_app_catalog_resource_version_info:
    listing_id: ocid1.appcataloglisting.oc1..example
    listing_resource_version: '1.0'
"""

RETURN = r"""
listing_resource_versions:
  description:
    - Resource versions that match the query.
    - List operations return summaries. Get operations return version details.
  returned: always
  type: list
  elements: dict
  contains:
    listing_id:
      description: The listing OCID.
      type: str
      returned: always
      sample: ocid1.appcataloglisting.oc1..example
    listing_resource_version:
      description: The resource version string.
      type: str
      returned: always
      sample: '1.0'
    listing_resource_id:
      description: The image resource OCID for use as oci_instance image_id.
      type: str
      returned: always
      sample: ocid1.image.oc1..example
    time_published:
      description: The publication time in RFC 3339 format.
      type: str
      returned: always
      sample: '2026-01-01T00:00:00+00:00'
    available_regions:
      description: Regions where the resource version is available.
      type: list
      elements: str
      returned: when a specific version is fetched
      sample: [us-phoenix-1]
    compatible_shapes:
      description: Shapes compatible with the resource version.
      type: list
      elements: str
      returned: when a specific version is fetched
      sample: [VM.Standard.E4.Flex]
    accessible_ports:
      description: Ports accessible for instances from this version.
      type: list
      elements: int
      returned: when a specific version is fetched
      sample: [22]
    allowed_actions:
      description: Actions allowed for the resource version.
      type: list
      elements: str
      returned: when a specific version is fetched
      sample: [launch]
  sample:
    - listing_id: ocid1.appcataloglisting.oc1..example
      listing_resource_version: '1.0'
      listing_resource_id: ocid1.image.oc1..example
      time_published: '2026-01-01T00:00:00+00:00'
    - listing_id: ocid1.appcataloglisting.oc1..example
      listing_resource_version: '1.0'
      listing_resource_id: ocid1.image.oc1..example
      time_published: '2026-01-01T00:00:00+00:00'
      available_regions: [us-phoenix-1]
      compatible_shapes: [VM.Standard.E4.Flex]
      accessible_ports: [22]
      allowed_actions: [launch]
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import OciInfoBase

oci = import_oci_sdk()[0]


class OciAppCatalogResourceVersionInfoModule(OciInfoBase):
    """Provide list and get operations for listing resource versions."""
    @property
    def client_class(self):
        """Return the client class for Compute App Catalog operations.

        Returns:
            The OCI Compute client class.
        """
        return oci.core.ComputeClient

    results_key = "listing_resource_versions"

    def fetch_resources(self):
        """Fetch versions using the listing ID and optional version.

        The inherited fetch operation supports one lookup identifier.

        Returns:
            All versions, one requested version, or an empty list if it is absent.
        """
        listing_id = self.module.params["listing_id"]
        version = self.module.params.get("listing_resource_version")
        if version is not None:
            return self.get_resource_by_id(
                (listing_id, version),
                self.client.get_app_catalog_listing_resource_version,
                listing_id=listing_id,
                resource_version=version,
            )
        return self.list_all_resources(
            self.client.list_app_catalog_listing_resource_versions,
            listing_id=listing_id,
        )


def main():
    """Run the App Catalog resource version info module."""
    module = AnsibleModule(
        argument_spec=dict(
            OCI_AUTH_ARGS,
            listing_id=dict(type="str", required=True),
            listing_resource_version=dict(type="str"),
        ),
        supports_check_mode=True,
    )
    OciAppCatalogResourceVersionInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
