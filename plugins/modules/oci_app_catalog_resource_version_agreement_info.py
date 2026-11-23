# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Retrieve OCI Compute App Catalog listing agreements."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_app_catalog_resource_version_agreement_info
short_description: Get OCI Compute App Catalog listing resource version agreements
description:
  - Retrieve the terms agreement for an App Catalog listing resource version.
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
      - The listing resource version for the agreement.
    type: str
    required: true
"""

EXAMPLES = r"""
- name: Retrieve listing terms
  ansible.oci.oci_app_catalog_resource_version_agreement_info:
    listing_id: ocid1.appcataloglisting.oc1..example
    listing_resource_version: '1.0'
  register: listing_agreement
  no_log: true
"""

RETURN = r"""
agreements:
  description: The agreement for the requested listing resource version.
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
      description: The listing resource version.
      type: str
      returned: always
      sample: '1.0'
    signature:
      description: The generated signature required by subscription creation.
      type: str
      returned: always
      sample: agreement-signature
    time_retrieved:
      description: The agreement retrieval time in RFC 3339 format.
      type: str
      returned: always
      sample: '2026-01-01T00:00:00+00:00'
    eula_link:
      description: The end-user license agreement link. This field can be null.
      type: str
      returned: always
      sample: https://example.com/eula
    oracle_terms_of_use_link:
      description: The Oracle terms of use link.
      type: str
      returned: always
      sample: https://www.oracle.com/legal/terms.html
  sample:
    - listing_id: ocid1.appcataloglisting.oc1..example
      listing_resource_version: '1.0'
      signature: agreement-signature
      time_retrieved: '2026-01-01T00:00:00+00:00'
      eula_link: https://example.com/eula
      oracle_terms_of_use_link: https://www.oracle.com/legal/terms.html
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import OciInfoBase

oci = import_oci_sdk()[0]


class OciAppCatalogResourceVersionAgreementInfoModule(OciInfoBase):
    """Provide agreement retrieval for a listing resource version."""
    @property
    def client_class(self):
        """Return the client class for Compute App Catalog operations.

        Returns:
            The OCI Compute client class.
        """
        return oci.core.ComputeClient

    results_key = "agreements"

    def fetch_resources(self):
        """Retrieve one agreement using its listing ID and version.

        The inherited fetch operation supports one lookup identifier.

        Returns:
            A one-item list with the agreement, or an empty list if it is absent.
        """
        listing_id = self.module.params["listing_id"]
        version = self.module.params["listing_resource_version"]
        return self.get_resource_by_id(
            (listing_id, version),
            self.client.get_app_catalog_listing_agreements,
            listing_id=listing_id,
            resource_version=version,
        )


def main():
    """Run the App Catalog agreement info module."""
    module = AnsibleModule(
        argument_spec=dict(
            OCI_AUTH_ARGS,
            listing_id=dict(type="str", required=True),
            listing_resource_version=dict(type="str", required=True),
        ),
        supports_check_mode=True,
    )
    OciAppCatalogResourceVersionAgreementInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
